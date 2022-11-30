"""Collection of tests for statistical functions."""
# global
import numpy as np
from hypothesis import strategies as st

# local
import ivy
import ivy_tests.test_ivy.helpers as helpers
from ivy_tests.test_ivy.helpers import handle_test


@st.composite
def statistical_dtype_values(draw, *, function):
    large_abs_safety_factor = 2
    small_abs_safety_factor = 2
    if function in ["mean", "std", "var"]:
        large_abs_safety_factor = 24
        small_abs_safety_factor = 24
    dtype, values, axis = draw(
        helpers.dtype_values_axis(
            available_dtypes=helpers.get_dtypes("float"),
            large_abs_safety_factor=large_abs_safety_factor,
            small_abs_safety_factor=small_abs_safety_factor,
            safety_factor_scale="log",
            min_num_dims=1,
            max_num_dims=5,
            min_dim_size=2,
            valid_axis=True,
            allow_neg_axes=False,
            min_axes_size=1,
        )
    )
    shape = values[0].shape
    size = values[0].size
    max_correction = np.min(shape)
    if function == "var" or function == "std":
        if size == 1:
            correction = 0
        elif isinstance(axis, int):
            correction = draw(
                helpers.ints(min_value=0, max_value=shape[axis] - 1)
                | helpers.floats(min_value=0, max_value=shape[axis] - 1)
            )
            return dtype, values, axis, correction
        else:
            correction = draw(
                helpers.ints(min_value=0, max_value=max_correction - 1)
                | helpers.floats(min_value=0, max_value=max_correction - 1)
            )
        return dtype, values, axis, correction
    return dtype, values, axis


@st.composite
def _get_castable_dtype(draw):
    available_dtypes = helpers.get_dtypes("numeric")
    shape = draw(helpers.get_shape(min_num_dims=1))
    dtype, values = draw(
        helpers.dtype_and_values(
            available_dtypes=available_dtypes,
            num_arrays=1,
            large_abs_safety_factor=6,
            small_abs_safety_factor=6,
            safety_factor_scale="log",
            shape=shape,
        )
    )
    axis = draw(helpers.get_axis(shape=shape, force_int=True))
    dtype1, values, dtype2 = draw(
        helpers.get_castable_dtype(draw(available_dtypes), dtype[0], values[0])
    )
    return dtype1, [values], axis, dtype2


# min
@handle_test(
    fn_tree="functional.ivy.min",
    dtype_and_x=statistical_dtype_values(function="min"),
    keep_dims=st.booleans(),
)
def test_min(
    *,
    dtype_and_x,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        x=x[0],
        axis=axis,
        keepdims=keep_dims,
    )


# max
@handle_test(
    fn_tree="functional.ivy.max",
    dtype_and_x=statistical_dtype_values(function="max"),
    num_positional_args=helpers.num_positional_args(fn_name="max"),
    keep_dims=st.booleans(),
)
def test_max(
    *,
    dtype_and_x,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        x=x[0],
        axis=axis,
        keepdims=keep_dims,
    )


# mean
@handle_test(
    fn_tree="functional.ivy.mean",
    dtype_and_x=statistical_dtype_values(function="mean"),
    keep_dims=st.booleans(),
)
def test_mean(
    *,
    dtype_and_x,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        rtol_=1e-1,
        atol_=1e-1,
        x=x[0],
        axis=axis,
        keepdims=keep_dims,
    )


# var
@handle_test(
    fn_tree="functional.ivy.var",
    dtype_and_x=statistical_dtype_values(function="var"),
    keep_dims=st.booleans(),
)
def test_var(
    *,
    dtype_and_x,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis, correction = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        rtol_=1e-1,
        atol_=1e-1,
        x=x[0],
        axis=axis,
        correction=correction,
        keepdims=keep_dims,
    )


# prod
@handle_test(
    fn_tree="functional.ivy.prod",
    dtype_x_axis_castable=_get_castable_dtype(),
    keep_dims=st.booleans(),
)
def test_prod(
    *,
    dtype_x_axis_castable,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis, castable_dtype = dtype_x_axis_castable
    # ToDo: set as_variable_flags as the parameter generated by test_prod once
    # this issue is marked as completed https://github.com/pytorch/pytorch/issues/75733
    if ivy.current_backend_str() == "torch":
        as_variable = [False]
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=[input_dtype],
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        rtol_=1e-1,
        atol_=1e-1,
        on_device=on_device,
        x=x[0],
        axis=axis,
        keepdims=keep_dims,
        dtype=castable_dtype,
    )


# sum
@handle_test(
    fn_tree="functional.ivy.sum",
    dtype_x_axis_castable=_get_castable_dtype(),
    keep_dims=st.booleans(),
)
def test_sum(
    *,
    dtype_x_axis_castable,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis, castable_dtype = dtype_x_axis_castable
    # ToDo: set as_variable_flags as the parameter generated by test_cumprod once
    # this issue is marked as completed https://github.com/pytorch/pytorch/issues/75733
    if ivy.current_backend_str() == "torch":
        as_variable = [False]
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=[input_dtype],
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        rtol_=1e-1,
        atol_=1e-2,
        x=x[0],
        axis=axis,
        keepdims=keep_dims,
        dtype=castable_dtype,
    )


# std
@handle_test(
    fn_tree="functional.ivy.std",
    dtype_and_x=statistical_dtype_values(function="std"),
    keep_dims=st.booleans(),
)
def test_std(
    *,
    dtype_and_x,
    keep_dims,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis, correction = dtype_and_x
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        rtol_=1e-1,
        atol_=1e-1,
        x=x[0],
        axis=axis,
        correction=correction,
        keepdims=keep_dims,
    )


@handle_test(
    fn_tree="functional.ivy.cumsum",
    dtype_x_axis_castable=_get_castable_dtype(),
    exclusive=st.booleans(),
    reverse=st.booleans(),
)
def test_cumsum(
    *,
    dtype_x_axis_castable,
    exclusive,
    reverse,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis, castable_dtype = dtype_x_axis_castable
    # ToDo: set as_variable_flags as the parameter generated by test_cumprod once
    # this issue is marked as completed https://github.com/pytorch/pytorch/issues/75733
    if ivy.current_backend_str() == "torch":
        as_variable = [False]
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=[input_dtype],
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        x=x[0],
        axis=axis,
        exclusive=exclusive,
        reverse=reverse,
        dtype=castable_dtype,
    )


# cumprod
@handle_test(
    fn_tree="functional.ivy.cumprod",
    dtype_x_axis_castable=_get_castable_dtype(),
    exclusive=st.booleans(),
    reverse=st.booleans(),
)
def test_cumprod(
    *,
    dtype_x_axis_castable,
    exclusive,
    reverse,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    input_dtype, x, axis, castable_dtype = dtype_x_axis_castable
    # ToDo: set as_variable_flags as the parameter generated by test_cumprod once
    # this issue is marked as completed https://github.com/pytorch/pytorch/issues/75733
    if ivy.current_backend_str() == "torch":
        as_variable = [False]
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=[input_dtype],
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=instance_method,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        x=x[0],
        axis=axis,
        exclusive=exclusive,
        reverse=reverse,
        dtype=castable_dtype,
    )


# TODO: add more general tests and fix get instance method testing passing
# einsum
@handle_test(
    fn_tree="functional.ivy.einsum",
    eq_n_op_n_shp=st.sampled_from(
        [
            ("ii", (np.arange(25).reshape(5, 5),), ()),
            ("ii->i", (np.arange(25).reshape(5, 5),), (5,)),
            ("ij,j", (np.arange(25).reshape(5, 5), np.arange(5)), (5,)),
        ]
    ),
    dtype=helpers.get_dtypes("float", full=False),
)
def test_einsum(
    *,
    eq_n_op_n_shp,
    dtype,
    as_variable,
    num_positional_args,
    native_array,
    container_flags,
    with_out,
    instance_method,
    backend_fw,
    fn_name,
    on_device,
    ground_truth_backend,
):
    eq, operands, true_shape = eq_n_op_n_shp
    kw = {}
    i = 0
    for x_ in operands:
        kw["x{}".format(i)] = x_
        i += 1
    # len(operands) + 1 because of the equation
    num_positional_args = len(operands) + 1
    helpers.test_function(
        ground_truth_backend=ground_truth_backend,
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container_flags,
        instance_method=False,
        fw=backend_fw,
        fn_name=fn_name,
        on_device=on_device,
        equation=eq,
        **kw,
    )
