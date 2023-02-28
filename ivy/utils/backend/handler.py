# global
import os
import sys
import copy
import types
import ivy
import importlib
import functools
import numpy as np
from typing import Optional
import gc
from ivy.utils import _importlib, verbosity
from ivy.utils.backend import ast_helpers

# local
from ivy.func_wrapper import _wrap_function

backend_stack = []
compiled_backends = {}
implicit_backend = "numpy"
ivy_original_dict = ivy.__dict__.copy()
ivy_original_fn_dict = dict()


class ContextManager:
    def __init__(self, module):
        self.module = module

    def __enter__(self):
        set_backend(self.module)

    def __exit__(self, exc_type, exc_val, exc_tb):
        unset_backend()


_array_types = dict()
_array_types["numpy"] = "ivy.functional.backends.numpy"
_array_types["jax.interpreters.xla"] = "ivy.functional.backends.jax"
_array_types["jaxlib.xla_extension"] = "ivy.functional.backends.jax"
_array_types["tensorflow.python.framework.ops"] = "ivy.functional.backends.tensorflow"
_array_types[
    "tensorflow.python.ops.resource_variable_ops"
] = "ivy.functional.backends.tensorflow"
_array_types["torch"] = "ivy.functional.backends.torch"
_array_types["torch.nn.parameter"] = "ivy.functional.backends.torch"
_array_types["mindspore"] = "ivy.functional.backends.mindspore"
_array_types["mindspore.common.tensor"] = "ivy.functional.backends.mindspore"

_backend_dict = dict()
_backend_dict["numpy"] = "ivy.functional.backends.numpy"
_backend_dict["jax"] = "ivy.functional.backends.jax"
_backend_dict["tensorflow"] = "ivy.functional.backends.tensorflow"
_backend_dict["torch"] = "ivy.functional.backends.torch"
_backend_dict["mindspore"] = "ivy.functional.backends.mindspore"

_backend_reverse_dict = dict()
_backend_reverse_dict["ivy.functional.backends.numpy"] = "numpy"
_backend_reverse_dict["ivy.functional.backends.jax"] = "jax"
_backend_reverse_dict["ivy.functional.backends.tensorflow"] = "tensorflow"
_backend_reverse_dict["ivy.functional.backends.torch"] = "torch"
_backend_reverse_dict["ivy.functional.backends.mindspore"] = "mindspore"

# Backend Getting/Setting #
# ----------------------- #


def prevent_access_locally(fn):
    @functools.wraps(fn)
    def new_fn(*args, **kwargs):
        if ivy.is_local():
            raise RuntimeError(f"Calling {fn.__name__} is not allowed on this object.")
        return fn(*args, **kwargs)

    return new_fn


def _determine_backend_from_args(args):
    """Return the appropriate Ivy backend, given some arguments.

    Parameters
    ----------
    args
        the arguments from which to figure out the corresponding Ivy backend.

    Returns
    -------
    ret
        the Ivy backend inferred from `args`.

    Examples
    --------
    If `args` is a jax.numpy array, then Ivy's jax backend will be returned:

    >>> from ivy.utils.backend.handler import _determine_backend_from_args
    >>> import jax.numpy as jnp
    >>> x = jnp.array([1])
    >>> print(_determine_backend_from_args(x))
    <module 'ivy.functional.backends.jax' from '/ivy/ivy/functional/backends/jax/__init__.py'>    # noqa

    """
    arg_type = type(args)
    if isinstance(args, ivy.Array):
        args = args.data

    if isinstance(args, dict):
        for key, value in args.items():
            # recursively call the function for each value in the dictionary
            lib = _determine_backend_from_args(value)
            if lib:
                return lib
        # check if args is a list or tuple
    elif arg_type in [list, tuple]:
        for arg in args:
            # recursively call the function for each element in the list/tuple
            lib = _determine_backend_from_args(arg)
            if lib:
                return lib
    else:
        # check if the class module of the arg is in _array_types
        if args.__class__.__module__ in _array_types:
            module_name = _array_types[args.__class__.__module__]
            return importlib.import_module(module_name)


def fn_name_from_version_specific_fn_name(name, version):
    """
    Parameters
    ----------
    name
        the version specific name of the function for which the version support
        is to be provided.
    version
        the version of the current framework for which the support is to be
        provided, the version is inferred by importing the framework
    Returns
    -------
        the name of the original function which will then point to the version
        specific function

    """
    # TODO: add tests
    version = str(version)
    if version.find("+") != -1:
        version = tuple(map(int, version[: version.index("+")].split(".")))
    else:
        version = tuple(map(int, version.split(".")))
    if "_to_" in name:
        i = name.index("_v_")
        e = name.index("_to_")
        version_start = name[i + 3 : e]
        version_start = tuple(map(int, version_start.split("p")))
        version_end = name[e + 4 :]
        version_end = tuple(map(int, version_end.split("p")))
        if version_start <= version <= version_end:
            return name[0:i]
    elif "_and_above" in name:
        i = name.index("_v_")
        e = name.index("_and_")
        version_start = name[i + 3 : e]
        version_start = tuple(map(int, version_start.split("p")))
        if version >= version_start:
            return name[0:i]
    else:
        i = name.index("_v_")
        e = name.index("_and_")
        version_start = name[i + 3 : e]
        version_start = tuple(map(int, version_start.split("p")))
        if version <= version_start:
            return name[0:i]


def set_backend_to_specific_version(backend):
    """
    Updates the backend dict to make the original function
    name point to the version specific one.

    Parameters
    ----------
    backend
        the backend module for which we provide the version support
    """
    # TODO: add functionality and tests
    f = str(backend.__name__)
    f = f[f.index("backends") + 9 :]

    f = importlib.import_module(f)
    f_version = f.__version__

    for key in list(backend.__dict__):
        if "_v_" in key:
            orig_name = fn_name_from_version_specific_fn_name(key, f_version)
            if orig_name:
                backend.__dict__[orig_name] = backend.__dict__[key]
                backend.__dict__[orig_name].__name__ = orig_name


def current_backend(*args, **kwargs):
    """Returns the current backend. Priorities:
    global_backend > argument's backend.

    Parameters
    ----------
    *args/**kwargs
        the arguments from which to try to infer the backend, when there is
        no globally set backend.

    Returns
    -------
    ret
        Ivy's current backend.

    Examples
    --------
    If no global backend is set, then the backend is inferred from the arguments:

    >>> import numpy as np
    >>> x = np.array([2.0])
    >>> print(ivy.current_backend(x))
    <module 'ivy.functional.backends.numpy' from '/ivy/ivy/functional/backends/numpy/__init__.py'>   # noqa

    The global backend set in set_backend has priority over any arguments
    passed to current_backend:

    >>> import numpy as np
    >>> ivy.set_backend("jax")
    >>> x = np.array([2.0])
    >>> print(ivy.current_backend(x))
    <module 'ivy.functional.backends.jax' from '/ivy/ivy/functional/backends/jax/__init__.py'>   # noqa
    """
    if ivy.is_local():
        return ivy
    global implicit_backend
    # if a global backend has been set with
    # set_backend then this will be returned
    if backend_stack:
        f = backend_stack[-1]
        if verbosity.level > 0:
            verbosity.cprint("Using backend from stack: {}".format(f))
        return f

    # if no global backend exists, we try to infer
    # the backend from the arguments
    f = _determine_backend_from_args(list(args) + list(kwargs.values()))
    if f is not None:
        implicit_backend = f.current_backend_str()
        return f
    if verbosity.level > 0:
        verbosity.cprint("Using backend from type: {}".format(f))
    return importlib.import_module(_backend_dict[implicit_backend])


def _set_backend_as_ivy(
    original_dict, target, backend, invalid_dtypes=None, backend_str=None
):
    invalid_dtypes = (
        backend.invalid_dtypes if invalid_dtypes is None else invalid_dtypes
    )
    backend_str = backend.current_backend_str() if backend_str is None else backend_str
    for k, v in original_dict.items():
        compositional = k not in backend.__dict__
        if k not in backend.__dict__:
            if k in invalid_dtypes and k in target.__dict__:
                del target.__dict__[k]
                continue
            backend.__dict__[k] = v
        target.__dict__[k] = _wrap_function(
            key=k, to_wrap=backend.__dict__[k], original=v, compositional=compositional
        )
        if (
            isinstance(v, types.ModuleType)
            and "ivy.functional." in v.__name__
            and os.path.join("{}", "__init__.py").format(backend_str) not in v.__file__
        ):
            _set_backend_as_ivy(
                v.__dict__,
                target.__dict__[k],
                backend.__dict__[k],
                invalid_dtypes=invalid_dtypes,
                backend_str=backend_str,
            )


def _handle_backend_specific_vars(backend):
    if backend.current_backend_str() == "numpy":
        backend.set_default_device("cpu")
    elif backend.current_backend_str() == "jax":
        backend.set_global_attr("RNG", backend.functional.backends.jax.random.RNG)


def convert_from_source_backend_to_numpy(variable_ids, numpy_objs):
    # Dynamic Backend
    from ivy.functional.ivy.gradients import _is_variable, _variable_data

    def _is_var(obj):
        if isinstance(obj, ivy.Container):

            def _map_fn(x):
                x = x.data if isinstance(x, ivy.Array) else x
                if x.__class__.__module__ in (
                    "numpy",
                    "jax.interpreters.xla",
                    "jaxlib.xla_extension",
                ):
                    return False

                return _is_variable(x)

            return obj.cont_map(lambda x, kc: _map_fn(x)).cont_all_true()

        else:
            obj = obj.data if isinstance(obj, ivy.Array) else obj
            if obj.__class__.__module__ in (
                "numpy",
                "jax.interpreters.xla",
                "jaxlib.xla_extension",
            ):
                return False
            return _is_variable(obj)

    def _remove_intermediate_arrays(arr_list, cont_list):
        cont_list = [cont.cont_to_flat_list() for cont in cont_list]

        cont_ids = [
            id(item.data) if isinstance(item, ivy.Array) else id(item)
            for cont in cont_list
            for item in cont
        ]
        arr_ids = [
            id(item.data) if isinstance(item, ivy.Array) else id(item)
            for item in arr_list
        ]

        new_objs = {k: v for k, v in zip(arr_ids, arr_list) if k not in cont_ids}

        return list(new_objs.values())

    # get all ivy array and container instances in the project scope
    array_list, container_list = [
        [obj for obj in gc.get_objects() if isinstance(obj, obj_type)]
        for obj_type in (ivy.Array, ivy.Container)
    ]

    # filter uninitialized arrays
    array_list = [arr for arr in array_list if arr.__dict__]

    # remove numpy intermediate objects
    new_objs = _remove_intermediate_arrays(array_list, container_list)
    new_objs += container_list

    # now convert all ivy.Array and ivy.Container instances
    # to numpy using the current backend
    for obj in new_objs:
        if obj.dynamic_backend:
            numpy_objs.append(obj)
            if _is_var(obj):
                # add variable object id to set
                variable_ids.add(id(obj))
                native_var = _variable_data(obj)
                np_data = ivy.to_numpy(native_var)

            else:
                np_data = obj.to_numpy()

            if isinstance(obj, ivy.Container):
                obj.cont_inplace_update(np_data)
            else:
                obj._data = np_data

    return variable_ids, numpy_objs


def convert_from_numpy_to_target_backend(variable_ids, numpy_objs):
    # Dynamic Backend
    from ivy.functional.ivy.gradients import _variable

    # convert all ivy.Array and ivy.Container instances from numpy
    # to native arrays using the newly set backend
    for obj in numpy_objs:
        np_arr = obj.data if isinstance(obj, ivy.Array) else obj
        # check if object was originally a variable
        if id(obj) in variable_ids:
            native_arr = ivy.nested_map(
                np_arr, current_backend().asarray, include_derived=True, shallow=False
            )
            new_data = _variable(native_arr)

        else:
            new_data = ivy.nested_map(
                np_arr, current_backend().asarray, include_derived=True, shallow=False
            )

        if isinstance(obj, ivy.Container):
            obj.cont_inplace_update(new_data)
        else:
            obj._data = new_data.data


@prevent_access_locally
def set_backend(backend: str, dynamic: bool = False):
    """Sets `backend` to be the global backend.
    Will also convert all Array and Container objects \
    to the new backend if `dynamic` = True

    Examples
    --------
    If we set the global backend to be numpy, then subsequent calls to ivy functions
    will be called from Ivy's numpy backend:

    >>> ivy.set_backend("numpy")
    >>> native = ivy.native_array([1])
    >>> print(type(native))
    <class 'numpy.ndarray'>

    Or with jax as the global backend:

    >>> ivy.set_backend("jax")
    >>> native = ivy.native_array([1])
    >>> print(type(native))
    <class 'jaxlib.xla_extension.DeviceArray'>
    """  # noqa
    ivy.utils.assertions.check_false(
        isinstance(backend, str) and backend not in _backend_dict,
        "backend must be one from {}".format(list(_backend_dict.keys())),
    )

    variable_ids = set()  # create an empty set to store variable object ids
    numpy_objs = []  # create an empty list to store numpy objects
    # created during 1st conversion step

    if dynamic:
        variable_ids, numpy_objs = convert_from_source_backend_to_numpy(
            variable_ids, numpy_objs
        )

    # update the global dict with the new backend
    ivy.locks["backend_setter"].acquire()
    global ivy_original_dict
    if not backend_stack:
        ivy_original_dict = ivy.__dict__.copy()
    if isinstance(backend, str):
        temp_stack = list()
        while backend_stack:
            temp_stack.append(unset_backend())
        backend = importlib.import_module(_backend_dict[backend])
        for fw in reversed(temp_stack):
            backend_stack.append(fw)
    if backend.current_backend_str() == "numpy":
        ivy.set_default_device("cpu")
    elif backend.current_backend_str() == "jax":
        ivy.set_global_attr("RNG", ivy.functional.backends.jax.random.RNG)
    backend_stack.append(backend)
    set_backend_to_specific_version(backend)
    _set_backend_as_ivy(ivy_original_dict, ivy, backend)

    if dynamic:
        convert_from_numpy_to_target_backend(variable_ids, numpy_objs)

    if verbosity.level > 0:
        verbosity.cprint("backend stack: {}".format(backend_stack))
    ivy.locks["backend_setter"].release()


def set_numpy_backend():
    """Sets NumPy to be the global backend. equivalent to `ivy.set_backend("numpy")`."""  # noqa
    set_backend("numpy")


def set_jax_backend():
    """Sets JAX to be the global backend. equivalent to `ivy.set_backend("jax")`."""  # noqa
    set_backend("jax")


def set_tensorflow_backend():
    """
    Sets TensorFlow to be the global backend. equivalent to
    `ivy.set_backend("tensorflow")`.
    """
    set_backend("tensorflow")


def set_torch_backend():
    """Sets torch to be the global backend. equivalent to `ivy.set_backend("torch")`."""  # noqa
    set_backend("torch")


def set_mindspore_backend():
    """
    Sets Mindspore to be the global backend. equivalent to
    `ivy.set_backend("mindspore")`.
    """
    set_backend("mindspore")


def get_backend(backend: Optional[str] = None):
    """Returns Ivy's backend for `backend` if specified, or if it isn't specified it
    returns the Ivy backend associated with the current globally set backend.

    Parameters
    ----------
    backend
        The backend for which we want to retrieve Ivy's backend i.e. one of 'jax',
        'torch', 'tensorflow', 'numpy'.

    Returns
    -------
    ret
        Ivy's backend for either `backend` or for the current global backend.

    Examples
    --------
    Global backend doesn't matter, if `backend` argument has been specified:

    >>> ivy.set_backend("jax")
    >>> ivy_np = ivy.get_backend("numpy")
    >>> print(ivy_np)
    <module 'ivy.functional.backends.numpy' from '/ivy/ivy/functional/backends/numpy/__init__.py'>   # noqa

    If backend isn't specified, the global backend is used:

    >>> ivy.set_backend("jax")
    >>> ivy_jax = ivy.get_backend()
    >>> print(ivy_jax)
    <module 'ivy.functional.backends.jax' from '/ivy/ivy/functional/backends/jax/__init__.py'>
    """  # noqa
    # ToDo: change this so that it doesn't depend at all on the global ivy.
    #  Currently all backend-agnostic implementations returned in this
    #  module will still use the global ivy backend.
    if ivy.is_local():
        return ivy
    global ivy_original_dict
    if not backend_stack:
        ivy_original_dict = ivy.__dict__.copy()
    # current global backend is retrieved if backend isn't specified,
    # otherwise `backend` argument will be used
    if backend is None:
        backend = ivy.current_backend()
        if not backend_stack:
            return ""
    elif isinstance(backend, str):
        backend = importlib.import_module(_backend_dict[backend])
    for k, v in ivy_original_dict.items():
        if k not in backend.__dict__:
            backend.__dict__[k] = v
    return backend


@prevent_access_locally
def unset_backend():
    """Unsets the current global backend, and adjusts the ivy dict such that either
    a previously set global backend is then used as the backend, otherwise we return
    to Ivy's implementations.

    Returns
    -------
    ret
        the backend that was unset, or None if there was no set global backend.

    Examples
    --------
    Torch is the last set backend hence is the backend used in the first examples.
    However, as seen in the example after, if `unset_backend` is called before
    `ivy.native_array` then tensorflow will become the current backend and any
    torch backend implementations in the Ivy dict will be swapped with the
    tensorflow implementation::

    >>> ivy.set_backend("tensorflow")
    >>> ivy.set_backend("torch")
    >>> x = ivy.native_array([1])
    >>> print(type(x))
    <class 'torch.Tensor'>

    >>> ivy.set_backend("tensorflow")
    >>> ivy.set_backend("torch")
    >>> ivy.unset_backend()
    >>> x = ivy.native_array([1])
    >>> print(type(x))
    <class'tensorflow.python.framework.ops.EagerTensor'>
    """  # noqa
    backend = None
    # if the backend stack is empty, nothing is done then we just return `None`
    if backend_stack:
        backend = backend_stack.pop(-1)  # remove last backend from the stack
        if backend.current_backend_str() == "numpy":
            ivy.unset_default_device()
        elif backend.current_backend_str() == "jax":
            ivy.del_global_attr("RNG")
        # the new backend is the backend that was set before the one
        # we just removed from the stack, or Ivy if there was no
        # previously set backend
        if backend_stack:
            new_backend = backend_stack[-1]
            if new_backend.current_backend_str() == "numpy":
                ivy.set_default_device("cpu")
            elif new_backend.current_backend_str() == "jax":
                ivy.set_global_attr("RNG", ivy.functional.backends.jax.random.RNG)
        new_backend_dict = (
            backend_stack[-1].__dict__ if backend_stack else ivy_original_dict
        )
        # wrap backend functions if there still is a backend, and add functions
        # to ivy namespace
        for k, v in new_backend_dict.items():
            if backend_stack and k in ivy_original_dict:
                v = _wrap_function(k, v, ivy_original_dict[k])
            if k in ivy_original_dict:
                ivy.__dict__[k] = v
    if verbosity.level > 0:
        verbosity.cprint("backend stack: {}".format(backend_stack))
    return backend


@prevent_access_locally
def clear_backend_stack():
    while backend_stack:
        unset_backend()


@prevent_access_locally
def choose_random_backend(excluded=None):
    excluded = list() if excluded is None else excluded
    while True:
        ivy.utils.assertions.check_equal(
            len(excluded),
            4,
            inverse=True,
            message="""Unable to select backend, all backends are excluded,\
            or not installed.""",
        )
        f = np.random.choice(
            [f_srt for f_srt in list(_backend_dict.keys()) if f_srt not in excluded]
        )
        if f is None:
            excluded.append(f)
            continue
        else:
            print("\nselected backend: {}\n".format(f))
            return f


# noinspection PyProtectedMember
@prevent_access_locally
def with_backend(backend: str):
    # TODO do error handling if finder fails
    finder = ast_helpers.IvyPathFinder()
    sys.meta_path.insert(0, finder)
    _importlib.path_hooks.insert(0, finder)
    ivy_pack = _importlib._import_module("ivy")
    ivy_pack._is_local_pkg = True
    backend_module = _importlib._import_module(
        ivy_pack.utils.backend.handler._backend_dict[backend], ivy_pack.__package__
    )
    _handle_backend_specific_vars(ivy_pack)
    # We know for sure that the backend stack is empty, no need to do backend unsetting
    ivy_pack.utils.backend.handler._set_backend_as_ivy(
        ivy_pack.__dict__.copy(), ivy_pack, backend_module
    )
    ivy_pack.backend_stack.append(backend_module)
    ivy_pack.utils.backend._importlib.import_cache = copy.copy(_importlib.import_cache)
    _importlib.path_hooks.remove(finder)
    sys.meta_path.remove(finder)
    _importlib._clear_cache()
    compiled_backends[f"{ivy_pack.backend}_{id(ivy_pack)}"] = ivy_pack
    return ivy_pack
