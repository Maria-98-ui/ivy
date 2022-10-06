"""Collection of tests for unified linear algebra functions."""


# global
import sys
import numpy as np
from hypothesis import given, assume, strategies as st

# local
import ivy
import ivy_tests.test_ivy.helpers as helpers
from ivy_tests.test_ivy.helpers import handle_cmd_line_args


@st.composite
def dtype_value1_value2_axis(
    draw,
    available_dtypes,
    min_value=None,
    max_value=None,
    allow_inf=False,
    exclude_min=False,
    exclude_max=False,
    min_num_dims=1,
    max_num_dims=10,
    min_dim_size=1,
    max_dim_size=10,
    specific_dim_size=3,
    large_abs_safety_factor=4,
    small_abs_safety_factor=4,
    safety_factor_scale="log",
):
    # For cross product, a dim with size 3 is required
    shape = draw(
        helpers.get_shape(
            allow_none=False,
            min_num_dims=min_num_dims,
            max_num_dims=max_num_dims,
            min_dim_size=min_dim_size,
            max_dim_size=max_dim_size,
        )
    )
    axis = draw(helpers.ints(min_value=0, max_value=len(shape)))
    # make sure there is a dim with specific dim size
    shape = list(shape)
    shape = shape[:axis] + [specific_dim_size] + shape[axis:]
    shape = tuple(shape)

    dtype = draw(st.sampled_from(draw(available_dtypes)))

    values = []
    for i in range(2):
        values.append(
            draw(
                helpers.array_values(
                    dtype=dtype,
                    shape=shape,
                    min_value=min_value,
                    max_value=max_value,
                    allow_inf=allow_inf,
                    exclude_min=exclude_min,
                    exclude_max=exclude_max,
                    large_abs_safety_factor=large_abs_safety_factor,
                    small_abs_safety_factor=small_abs_safety_factor,
                    safety_factor_scale=safety_factor_scale,
                )
            )
        )

    value1, value2 = values[0], values[1]
    return [dtype], value1, value2, axis


@st.composite
def _get_dtype_value1_value2_axis_for_tensordot(
    draw,
    available_dtypes,
    min_value=None,
    max_value=None,
    allow_inf=False,
    exclude_min=False,
    exclude_max=False,
    min_num_dims=1,
    max_num_dims=10,
    min_dim_size=1,
    max_dim_size=10,
):

    shape = draw(
        helpers.get_shape(
            allow_none=False,
            min_num_dims=min_num_dims,
            max_num_dims=max_num_dims,
            min_dim_size=min_dim_size,
            max_dim_size=max_dim_size,
        )
    )
    axis = draw(helpers.ints(min_value=1, max_value=len(shape)))
    dtype = draw(st.sampled_from(draw(available_dtypes)))

    values = []
    for i in range(2):
        values.append(
            draw(
                helpers.array_values(
                    dtype=dtype,
                    shape=shape,
                    min_value=min_value,
                    max_value=max_value,
                    allow_inf=allow_inf,
                    exclude_min=exclude_min,
                    exclude_max=exclude_max,
                    large_abs_safety_factor=72,
                    small_abs_safety_factor=72,
                    safety_factor_scale="log",
                )
            )
        )

    value1, value2 = values[0], values[1]
    if not isinstance(axis, list):
        value2 = value2.transpose(
            [k for k in range(len(shape) - axis, len(shape))]
            + [k for k in range(0, len(shape) - axis)]
        )
    return [dtype], value1, value2, axis


@st.composite
def _get_dtype_and_matrix(draw, *, symmetric=False):
    # batch_shape, shared, random_size
    input_dtype = draw(st.shared(st.sampled_from(draw(helpers.get_dtypes("float")))))
    random_size = draw(helpers.ints(min_value=2, max_value=4))
    batch_shape = draw(helpers.get_shape(min_num_dims=1, max_num_dims=3))
    if symmetric:
        num_independnt_vals = int((random_size**2) / 2 + random_size / 2)
        array_vals_flat = np.array(
            draw(
                helpers.array_values(
                    dtype=input_dtype,
                    shape=tuple(list(batch_shape) + [num_independnt_vals]),
                    min_value=2,
                    max_value=5,
                )
            )
        )
        array_vals = np.zeros(batch_shape + (random_size, random_size))
        c = 0
        for i in range(random_size):
            for j in range(random_size):
                if j < i:
                    continue
                array_vals[..., i, j] = array_vals_flat[..., c]
                array_vals[..., j, i] = array_vals_flat[..., c]
                c += 1
        return [input_dtype], array_vals
    return [input_dtype], draw(
        helpers.array_values(
            dtype=input_dtype,
            shape=tuple(list(batch_shape) + [random_size, random_size]),
            min_value=2,
            max_value=5,
        )
    )


@st.composite
def _get_first_matrix_and_dtype(draw):
    # batch_shape, random_size, shared
    input_dtype = draw(
        st.shared(
            st.sampled_from(draw(helpers.get_dtypes("numeric"))),
            key="shared_dtype",
        )
    )
    shared_size = draw(
        st.shared(helpers.ints(min_value=2, max_value=4), key="shared_size")
    )
    random_size = draw(helpers.ints(min_value=2, max_value=4))
    batch_shape = draw(
        st.shared(helpers.get_shape(min_num_dims=1, max_num_dims=3), key="shape")
    )
    return [input_dtype], draw(
        helpers.array_values(
            dtype=input_dtype,
            shape=tuple(list(batch_shape) + [random_size, shared_size]),
            min_value=2,
            max_value=5,
        )
    )


@st.composite
def _get_second_matrix_and_dtype(draw):
    # batch_shape, shared, random_size
    input_dtype = draw(
        st.shared(
            st.sampled_from(draw(helpers.get_dtypes("numeric"))),
            key="shared_dtype",
        )
    )
    shared_size = draw(
        st.shared(helpers.ints(min_value=2, max_value=4), key="shared_size")
    )
    random_size = draw(helpers.ints(min_value=2, max_value=4))
    batch_shape = draw(
        st.shared(helpers.get_shape(min_num_dims=1, max_num_dims=3), key="shape")
    )
    return [input_dtype], draw(
        helpers.array_values(
            dtype=input_dtype,
            shape=tuple(list(batch_shape) + [shared_size, random_size]),
            min_value=2,
            max_value=5,
        )
    )


# vector_to_skew_symmetric_matrix
@st.composite
def _get_dtype_and_vector(draw):
    # batch_shape, shared, random_size
    input_dtype = draw(
        st.shared(
            st.sampled_from(draw(helpers.get_dtypes("numeric"))),
            key="shared_dtype",
        )
    )
    batch_shape = draw(helpers.get_shape(min_num_dims=2, max_num_dims=4))
    return [input_dtype], draw(
        helpers.array_values(
            dtype=input_dtype,
            shape=tuple(list(batch_shape) + [3]),
            min_value=2,
            max_value=5,
        )
    )


@handle_cmd_line_args
@given(
    dtype_x=_get_dtype_and_vector(),
    num_positional_args=helpers.num_positional_args(
        fn_name="vector_to_skew_symmetric_matrix"
    ),
)
def test_vector_to_skew_symmetric_matrix(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="vector_to_skew_symmetric_matrix",
        vector=x,
    )


# matrix_power
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_value=0,
        max_value=50,
        shape=helpers.ints(min_value=2, max_value=8).map(lambda x: tuple([x, x])),
    ),
    n=helpers.ints(min_value=1, max_value=8),
    num_positional_args=helpers.num_positional_args(fn_name="matrix_power"),
)
def test_matrix_power(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    n,
):
    dtype, x = dtype_x

    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="matrix_power",
        rtol_=1e-1,
        atol_=1e-1,
        x=x[0],
        n=n,
    )


# matmul
@handle_cmd_line_args
@given(
    x=_get_first_matrix_and_dtype(),
    y=_get_second_matrix_and_dtype(),
    num_positional_args=helpers.num_positional_args(fn_name="matmul"),
)
def test_matmul(
    *,
    x,
    y,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype1, x_1 = x
    input_dtype2, y_1 = y
    helpers.test_function(
        input_dtypes=input_dtype1 + input_dtype2,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="matmul",
        rtol_=1e-1,
        atol_=1e-1,
        x1=x_1,
        x2=y_1,
    )


# det
@handle_cmd_line_args
@given(
    dtype_x=_get_dtype_and_matrix(),
    num_positional_args=helpers.num_positional_args(fn_name="det"),
)
def test_det(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="det",
        rtol_=1e-3,
        atol_=1e-3,
        x=x,
    )


# eigh
@handle_cmd_line_args
@given(
    dtype_x=_get_dtype_and_matrix(symmetric=True),
    UPLO=st.sampled_from(("L", "U")),
    num_positional_args=helpers.num_positional_args(fn_name="eigh"),
)
def test_eigh(
    *,
    dtype_x,
    UPLO,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    results = helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="eigh",
        x=x,
        UPLO=UPLO,
        test_values=False,
        return_flat_np_arrays=True,
    )
    if results is None:
        return
    ret_np_flat, ret_from_np_flat = results
    eigenvalues_np, eigenvectors_np = ret_np_flat
    reconstructed_np = None
    for eigenvalue, eigenvector in zip(eigenvalues_np, eigenvectors_np):
        if reconstructed_np is not None:
            reconstructed_np += eigenvalue * np.matmul(
                eigenvector.reshape(1, -1), eigenvector.reshape(-1, 1)
            )
        else:
            reconstructed_np = eigenvalue * np.matmul(
                eigenvector.reshape(1, -1), eigenvector.reshape(-1, 1)
            )
    eigenvalues_from_np, eigenvectors_from_np = ret_from_np_flat
    reconstructed_from_np = None
    for eigenvalue, eigenvector in zip(eigenvalues_from_np, eigenvectors_from_np):
        if reconstructed_from_np is not None:
            reconstructed_from_np += eigenvalue * np.matmul(
                eigenvector.reshape(1, -1), eigenvector.reshape(-1, 1)
            )
        else:
            reconstructed_from_np = eigenvalue * np.matmul(
                eigenvector.reshape(1, -1), eigenvector.reshape(-1, 1)
            )
    # value test
    helpers.assert_all_close(
        reconstructed_np, reconstructed_from_np, rtol=1e-1, atol=1e-2
    )


# eigvalsh
@handle_cmd_line_args
@given(
    dtype_x=_get_dtype_and_matrix(symmetric=True),
    UPLO=st.sampled_from(("L", "U")),
    num_positional_args=helpers.num_positional_args(fn_name="eigvalsh"),
)
def test_eigvalsh(
    *,
    dtype_x,
    UPLO,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="eigvalsh",
        rtol_=1e-3,
        test_values=False,
        x=x,
        UPLO=UPLO,
    )


# inner
@handle_cmd_line_args
@given(
    dtype_xy=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
        num_arrays=2,
        large_abs_safety_factor=8,
        small_abs_safety_factor=8,
        safety_factor_scale="log",
        min_num_dims=1,
        max_num_dims=1,
    ),
    num_positional_args=helpers.num_positional_args(fn_name="inner"),
)
def test_inner(
    *,
    dtype_xy,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    types, arrays = dtype_xy
    helpers.test_function(
        input_dtypes=types,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="inner",
        rtol_=1e-1,
        atol_=1e-2,
        x1=arrays[0],
        x2=arrays[1],
    )


# inv
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        small_abs_safety_factor=2,
        safety_factor_scale="log",
        shape=helpers.ints(min_value=2, max_value=20).map(lambda x: tuple([x, x])),
    ).filter(lambda x: np.linalg.cond(x[1][0].tolist()) < 1 / sys.float_info.epsilon),
    adjoint=st.booleans(),
    num_positional_args=helpers.num_positional_args(fn_name="inv"),
)
def test_inv(
    *,
    dtype_x,
    adjoint,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        rtol_=1e-2,
        atol_=1e-2,
        fn_name="inv",
        x=x[0],
        adjoint=adjoint,
    )


# matrix_transpose
@handle_cmd_line_args
@given(
    dtype_x=_get_first_matrix_and_dtype(),
    num_positional_args=helpers.num_positional_args(fn_name="matrix_transpose"),
)
def test_matrix_transpose(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="matrix_transpose",
        x=x,
    )


# outer
@handle_cmd_line_args
@given(
    dtype_xy=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
        num_arrays=2,
        min_value=1,
        max_value=50,
        min_num_dims=1,
        max_num_dims=1,
    ),
    num_positional_args=helpers.num_positional_args(fn_name="outer"),
)
def test_outer(
    *,
    dtype_xy,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    types, arrays = dtype_xy
    helpers.test_function(
        input_dtypes=types,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="outer",
        x1=arrays[0],
        x2=arrays[1],
    )


# slogdet
# TODO: add with_out testing when testing with tuples is supported
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        small_abs_safety_factor=72,
        large_abs_safety_factor=72,
        safety_factor_scale="log",
        shape=helpers.ints(min_value=2, max_value=20).map(lambda x: tuple([x, x])),
    ),
    num_positional_args=helpers.num_positional_args(fn_name="slogdet"),
)
def test_slogdet(
    *,
    dtype_x,
    as_variable,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=False,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        rtol_=1e-1,
        atol_=1e-2,
        fn_name="slogdet",
        x=x[0],
    )


# solve
@st.composite
def _get_first_matrix(draw):
    # batch_shape, random_size, shared
    input_dtype = draw(
        st.shared(
            st.sampled_from(draw(helpers.get_dtypes("float"))), key="shared_dtype"
        )
    )
    shared_size = draw(
        st.shared(helpers.ints(min_value=2, max_value=4), key="shared_size")
    )
    return [input_dtype], draw(
        helpers.array_values(
            dtype=input_dtype,
            shape=tuple([shared_size, shared_size]),
            min_value=2,
            max_value=5,
        ).filter(lambda x: np.linalg.cond(x) < 1 / sys.float_info.epsilon)
    )


@st.composite
def _get_second_matrix(draw):
    # batch_shape, shared, random_size
    input_dtype = draw(
        st.shared(
            st.sampled_from(draw(helpers.get_dtypes("float"))), key="shared_dtype"
        )
    )
    shared_size = draw(
        st.shared(helpers.ints(min_value=2, max_value=4), key="shared_size")
    )
    return [input_dtype], draw(
        helpers.array_values(
            dtype=input_dtype, shape=tuple([shared_size, 1]), min_value=2, max_value=5
        )
    )


@handle_cmd_line_args
@given(
    x=_get_first_matrix(),
    y=_get_second_matrix(),
    num_positional_args=helpers.num_positional_args(fn_name="solve"),
)
def test_solve(
    *,
    x,
    y,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype1, x1 = x
    input_dtype2, x2 = y
    helpers.test_function(
        input_dtypes=input_dtype1 + input_dtype2,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="solve",
        rtol_=1e-1,
        atol_=1e-1,
        x1=x1[0],
        x2=x2[0],
    )


# svdvals
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_value=0,
        max_value=50,
        min_num_dims=2,
    ),
    num_positional_args=helpers.num_positional_args(fn_name="svdvals"),
)
def test_svdvals(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    input_dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=input_dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="svdvals",
        rtol_=1e-2,
        atol_=1e-2,
        x=x[0],
    )


# tensordot
@handle_cmd_line_args
@given(
    dtype_x1_x2_axis=_get_dtype_value1_value2_axis_for_tensordot(
        available_dtypes=helpers.get_dtypes("numeric"),
        min_num_dims=1,
        max_num_dims=5,
        min_dim_size=1,
        max_dim_size=10,
    ),
    num_positional_args=helpers.num_positional_args(fn_name="tensordot"),
)
def test_tensordot(
    *,
    dtype_x1_x2_axis,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):

    (
        dtype,
        x1,
        x2,
        axis,
    ) = dtype_x1_x2_axis

    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="tensordot",
        rtol_=5e-1,
        atol_=5e-1,
        x1=x1,
        x2=x2,
        axes=axis,
    )


# trace
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_num_dims=2,
        max_num_dims=2,
        min_dim_size=1,
        max_dim_size=10,
        large_abs_safety_factor=1.1,
        small_abs_safety_factor=1.1,
        safety_factor_scale="linear",
    ),
    offset=st.integers(min_value=0, max_value=0),
    axis1=st.integers(min_value=0, max_value=0),
    axis2=st.integers(min_value=1, max_value=1),
    num_positional_args=helpers.num_positional_args(fn_name="trace"),
)
def test_trace(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    offset,
    axis1,
    axis2,
):
    dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="trace",
        rtol_=1e-2,
        atol_=1e-2,
        x=x[0],
        offset=offset,
        axis1=axis1,
        axis2=axis2,
    )


# vecdot
@handle_cmd_line_args
@given(
    dtype_x1_x2_axis=dtype_value1_value2_axis(
        available_dtypes=helpers.get_dtypes("numeric"),
        large_abs_safety_factor=100,
        small_abs_safety_factor=100,
        safety_factor_scale="log",
        min_num_dims=1,
        max_num_dims=5,
        min_dim_size=1,
        max_dim_size=5,
    ),
    num_positional_args=helpers.num_positional_args(fn_name="vecdot"),
)
def test_vecdot(
    *,
    dtype_x1_x2_axis,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    dtype, x1, x2, axis = dtype_x1_x2_axis
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="vecdot",
        rtol_=5e-1,
        atol_=5e-1,
        x1=x1,
        x2=x2,
        axis=axis,
    )


# vector_norm
@handle_cmd_line_args
@given(
    dtype_values_axis=helpers.dtype_values_axis(
        available_dtypes=helpers.get_dtypes("float"),
        min_num_dims=2,
        max_num_dims=3,
        min_dim_size=2,
        max_dim_size=5,
        min_axis=-2,
        max_axis=1,
    ),
    kd=st.booleans(),
    ord=helpers.ints(min_value=1, max_value=2),
    num_positional_args=helpers.num_positional_args(fn_name="vector_norm"),
)
def test_vector_norm(
    *,
    dtype_values_axis,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    kd,
    ord,
):
    dtype, x, axis = dtype_values_axis
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="vector_norm",
        rtol_=1e-2,
        atol_=1e-2,
        x=x[0],
        axis=axis,
        keepdims=kd,
        ord=ord,
    )


# pinv
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_num_dims=2,
        max_num_dims=5,
        min_dim_size=1,
        max_dim_size=5,
        large_abs_safety_factor=32,
        small_abs_safety_factor=32,
        safety_factor_scale="log",
    ),
    rtol=st.floats(1e-5, 1e-3),
    num_positional_args=helpers.num_positional_args(fn_name="pinv"),
)
def test_pinv(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    rtol,
):
    dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="pinv",
        rtol_=1e-2,
        atol_=1e-2,
        x=x[0],
        rtol=rtol,
    )


# qr
@handle_cmd_line_args
@given(
    dtype_x=_get_dtype_and_matrix(),
    mode=st.sampled_from(("reduced", "complete")),
    num_positional_args=helpers.num_positional_args(fn_name="qr"),
)
def test_qr(
    *,
    dtype_x,
    as_variable,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    mode,
):
    dtype, x = dtype_x
    results = helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=False,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="qr",
        x=x,
        mode=mode,
        test_values=False,
        return_flat_np_arrays=True,
    )
    if results is None:
        return

    ret_np_flat, ret_from_np_flat = results

    q_np_flat, r_np_flat = ret_np_flat
    q_from_np_flat, r_from_np_flat = ret_from_np_flat

    reconstructed_np_flat = np.matmul(q_np_flat, r_np_flat)
    reconstructed_from_np_flat = np.matmul(q_from_np_flat, r_from_np_flat)

    # value test
    helpers.assert_all_close(
        reconstructed_np_flat, reconstructed_from_np_flat, rtol=1e-2, atol=1e-2
    )


# svd
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_num_dims=3,
        max_num_dims=5,
        min_dim_size=2,
        max_dim_size=5,
        min_value=0.1,
        max_value=10.0,
    ),
    fm=st.booleans(),
    uv=st.booleans(),
    num_positional_args=helpers.num_positional_args(
        fn_name="svd",
    ),
)
def test_svd(
    *,
    dtype_x,
    as_variable,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    uv,
    fm,
):
    dtype, x = dtype_x

    results = helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=False,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="svd",
        x=x[0],
        compute_uv=uv,
        full_matrices=fm,
        test_values=False,
        return_flat_np_arrays=True,
    )
    if results is None:
        return

    # value test based on recreating the original matrix and testing the consistency
    ret_flat_np, ret_from_gt_flat_np = results

    if uv:
        U, S, Vh = ret_flat_np
        m = U.shape[-1]
        n = Vh.shape[-1]
        S = np.expand_dims(S, -2) if m > n else np.expand_dims(S, -1)
        U_gt, S_gt, Vh_gt = ret_from_gt_flat_np
        S_gt = np.expand_dims(S_gt, -2) if m > n else np.expand_dims(S_gt, -1)

        with ivy.functional.backends.numpy.use:
            S_mat = (
                S * ivy.eye(U.shape[-1], Vh.shape[-2], batch_shape=U.shape[:-2]).data
            )
            S_mat_gt = (
                S_gt
                * ivy.eye(
                    U_gt.shape[-1], Vh_gt.shape[-2], batch_shape=U_gt.shape[:-2]
                ).data
            )
        reconstructed = np.matmul(np.matmul(U, S_mat), Vh)
        reconstructed_gt = np.matmul(np.matmul(U_gt, S_mat_gt), Vh_gt)

        # value test
        helpers.assert_all_close(reconstructed, reconstructed_gt, atol=1e-04)
        helpers.assert_all_close(reconstructed, x[0], atol=1e-04)
    else:
        S = ret_flat_np
        S_gt = ret_from_gt_flat_np
        helpers.assert_all_close(S[0], S_gt[0], atol=1e-04)


# matrix_norm
@handle_cmd_line_args
@given(
    dtype_value_shape=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        shape=st.shared(helpers.get_shape(min_num_dims=2, max_num_dims=2), key="shape"),
        min_num_dims=2,
        max_num_dims=2,
        min_dim_size=1,
        max_dim_size=10,
    ),
    kd=st.booleans(),
    axis=st.just((-2, -1)),
    ord=helpers.ints(min_value=1, max_value=2) | st.sampled_from(("fro", "nuc")),
    num_positional_args=helpers.num_positional_args(fn_name="matrix_norm"),
)
def test_matrix_norm(
    *,
    dtype_value_shape,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    kd,
    axis,
    ord,
):
    dtype, x = dtype_value_shape
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="matrix_norm",
        x=x[0],
        axis=axis,
        keepdims=kd,
        ord=ord,
    )


@st.composite
def _matrix_rank_helper(draw):
    dtype_x = draw(
        helpers.dtype_and_values(
            available_dtypes=helpers.get_dtypes("float"),
            min_num_dims=2,
            shape=helpers.ints(min_value=2, max_value=20).map(lambda x: tuple([x, x])),
            large_abs_safety_factor=48,
            small_abs_safety_factor=48,
            safety_factor_scale="log",
        )
    )
    return dtype_x


# matrix_rank
@handle_cmd_line_args
@given(
    dtype_x=_matrix_rank_helper(),
    atol=st.floats(min_value=0.0, max_value=0.1, exclude_min=True, exclude_max=True)
    | st.just(None),
    rtol=st.floats(min_value=0.0, max_value=0.1, exclude_min=True, exclude_max=True)
    | st.just(None),
    num_positional_args=helpers.num_positional_args(fn_name="matrix_rank"),
)
def test_matrix_rank(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    atol,
    rtol,
):
    dtype, x = dtype_x
    x_temp = x[0]
    for x_i in x_temp.reshape(-1, *x_temp.shape[-2:]):
        assume(round(np.linalg.det(x_i.astype("float64")), 1) != 0.0)
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="matrix_rank",
        x=x[0],
        atol=atol,
        rtol_=rtol,
    )


# cholesky
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("float"),
        min_value=0,
        max_value=10,
        shape=helpers.ints(min_value=2, max_value=5).map(lambda x: tuple([x, x])),
    ),
    upper=st.booleans(),
    num_positional_args=helpers.num_positional_args(fn_name="cholesky"),
)
def test_cholesky(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    upper,
):
    dtype, x = dtype_x
    x = x[0]
    x = (
        np.matmul(x.T, x) + np.identity(x.shape[0]) * 1e-3
    )  # make symmetric positive-definite

    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="cholesky",
        x=x,
        upper=upper,
        rtol_=1e-3,
        atol_=1e-3,
    )


# cross
@handle_cmd_line_args
@given(
    dtype_x1_x2_axis=dtype_value1_value2_axis(
        available_dtypes=helpers.get_dtypes("numeric"),
        min_num_dims=1,
        max_num_dims=10,
        min_dim_size=3,
        max_dim_size=3,
        large_abs_safety_factor=48,
        small_abs_safety_factor=48,
        safety_factor_scale="log",
    ),
    num_positional_args=helpers.num_positional_args(fn_name="cross"),
)
def test_cross(
    *,
    dtype_x1_x2_axis,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
):
    dtype, x1, x2, axis = dtype_x1_x2_axis
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="cross",
        rtol_=1e-1,
        atol_=1e-2,
        x1=x1,
        x2=x2,
        axis=axis,
    )


@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
    ),
    dtype_offset=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("integer"),
        max_num_dims=1,
        min_num_dims=1,
        min_dim_size=1,
    ),
    dtype_padding_value=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
    ),
    align=st.sampled_from(["RIGHT_LEFT", "RIGHT_RIGHT", "LEFT_LEFT", "LEFT_RIGHT"]),
    num_rows=helpers.ints(min_value=1),
    num_cols=helpers.ints(min_value=1),
    num_positional_args=helpers.num_positional_args(fn_name="diag"),
)
def test_diag(
    *,
    dtype_x,
    dtype_offset,
    dtype_padding_value,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    align,
    num_rows,
    num_cols,
):
    x_dtype, x = dtype_x
    offset_dtype, offset = dtype_offset
    padding_value_dtype, padding_value = dtype_padding_value
    helpers.test_function(
        input_dtypes=[dtype_x, offset_dtype, dtype_padding_value],
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="diagonal",
        x=x,
        offset=offset,
        align=align,
        num_rows=num_rows,
        num_cols=num_cols,
    )


# diagonal
@handle_cmd_line_args
@given(
    dtype_x=helpers.dtype_and_values(
        available_dtypes=helpers.get_dtypes("numeric"),
        min_num_dims=2,
        max_num_dims=2,
        min_dim_size=1,
        max_dim_size=50,
    ),
    offset=helpers.ints(min_value=-10, max_value=50),
    axes=st.lists(
        helpers.ints(min_value=-2, max_value=1), min_size=2, max_size=2, unique=True
    ).filter(lambda axes: axes[0] % 2 != axes[1] % 2),
    num_positional_args=helpers.num_positional_args(fn_name="diagonal"),
)
def test_diagonal(
    *,
    dtype_x,
    as_variable,
    with_out,
    num_positional_args,
    native_array,
    container,
    instance_method,
    fw,
    offset,
    axes,
):
    dtype, x = dtype_x
    helpers.test_function(
        input_dtypes=dtype,
        as_variable_flags=as_variable,
        with_out=with_out,
        num_positional_args=num_positional_args,
        native_array_flags=native_array,
        container_flags=container,
        instance_method=instance_method,
        fw=fw,
        fn_name="diagonal",
        x=x[0],
        offset=offset,
        axis1=axes[0],
        axis2=axes[1],
    )
