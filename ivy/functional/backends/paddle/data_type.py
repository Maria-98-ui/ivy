# global
from typing import Optional, Union, Sequence, List

import paddle
import numpy as np
# local
import ivy
from ivy.func_wrapper import with_unsupported_dtypes
from ivy.functional.ivy.data_type import _handle_nestable_dtype_info
from . import backend_version
from ivy.utils.exceptions import IvyNotImplementedException


ivy_dtype_dict = {
    paddle.int8: "int8",
    paddle.int16: "int16",
    paddle.int32: "int32",
    paddle.int64: "int64",
    paddle.uint8: "uint8",
    paddle.float16: "float16",
    paddle.float32: "float32",
    paddle.float64: "float64",
    paddle.complex64: "complex64",
    paddle.complex128: "complex128",
    paddle.bool: "bool",
}

native_dtype_dict = {
    "int8": paddle.int8,
    "int16": paddle.int16,
    "int32": paddle.int32,
    "int64": paddle.int64,
    "uint8": paddle.uint8,
    "float16": paddle.float16,
    "float32": paddle.float32,
    "float64": paddle.float64,
    "complex64": paddle.complex64,
    "complex128": paddle.complex128,
    "bool": paddle.bool,
}


class Finfo:
    def __init__(self, paddle_finfo: np.finfo):
        self._paddle_finfo = paddle_finfo

    def __repr__(self):
        return repr(self._paddle_finfo)

    @property
    def bits(self):
        return self._paddle_finfo.bits

    @property
    def eps(self):
        return float(self._paddle_finfo.eps)

    @property
    def max(self):
        return float(self._paddle_finfo.max)

    @property
    def min(self):
        return float(self._paddle_finfo.min)

    @property
    def smallest_normal(self):
        return float(self._paddle_finfo.tiny)


class Iinfo:
    def __init__(self, paddle_iinfo: np.iinfo):
        self._paddle_iinfo = paddle_iinfo

    def __repr__(self):
        return repr(self._paddle_iinfo)

    @property
    def bits(self):
        return self._paddle_iinfo.bits

    @property
    def max(self):
        return self._paddle_iinfo.max

    @property
    def min(self):
        return self._paddle_iinfo.min


class Bfloat16Finfo:
    def __init__(self):
        self.resolution = 0.01
        self.bits = 16
        self.eps = 0.0078125
        self.max = 3.38953e38
        self.min = -3.38953e38
        self.tiny = 1.17549e-38

    def __repr__(self):
        return "finfo(resolution={}, min={}, max={}, dtype={})".format(
            self.resolution, self.min, self.max, "bfloat16"
        )


# Array API Standard #
# -------------------#


def astype(
    x: paddle.Tensor,
    dtype: paddle.dtype,
    /,
    *,
    copy: bool = True,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    dtype = ivy.as_native_dtype(dtype)
    if x.dtype == dtype:
        return x.clone() if copy else x
    return x.cast(dtype)


@with_unsupported_dtypes(
    {"2.4.2 and below": ("int8", "int16", "uint8", "uint16",
                         "bfloat16", "float16", "complex64", "complex128")},
    backend_version,
)
def broadcast_arrays(*arrays: paddle.Tensor) -> List[paddle.Tensor]:
    new_arrays = []
    for array in arrays:
        if isinstance(array, paddle.Tensor):
            if array.rank().item() == 0:
                if array.dtype in [paddle.int16, paddle.float16]:
                    array, array_dtype = array.astype('float32'), array.dtype
                    new_arrays.append(array.unsqueeze(0).astype(array_dtype))
                else:
                    new_arrays.append(array.unsqueeze(0))
            else:
                new_arrays.append(array)
        else:
            new_arrays.append(paddle.to_tensor(array))
    return list(paddle.broadcast_tensors(new_arrays))


def broadcast_to(
    x: paddle.Tensor,
    /,
    shape: Union[ivy.NativeShape, Sequence[int]],
    *,
    out: Optional[paddle.Tensor] = None,
) -> paddle.Tensor:
    if x.ndim > len(shape):
        return paddle.broadcast_to(x.reshape([-1]), shape)
    return paddle.broadcast_to(x, shape)


@_handle_nestable_dtype_info
def finfo(type: Union[paddle.dtype, str, paddle.Tensor], /) -> Finfo:
    if isinstance(type, paddle.Tensor):
        type = str(type.dtype)[7:]
    elif isinstance(type, paddle.dtype):
        type = str(type)[7:]

    if ivy.as_native_dtype(type) == paddle.bfloat16:
        return Finfo(Bfloat16Finfo())

    return Finfo(np.finfo(type))


@_handle_nestable_dtype_info
def iinfo(type: Union[paddle.dtype, str, paddle.Tensor], /) -> Iinfo:
    if isinstance(type, paddle.Tensor):
        type = str(type.dtype)[7:]
    elif isinstance(type, paddle.dtype):
        type = str(type)[7:]

    return Iinfo(np.iinfo(type))


def result_type(*arrays_and_dtypes: Union[paddle.Tensor, paddle.dtype]) -> ivy.Dtype:
    input = []
    for val in arrays_and_dtypes:
        paddle_val = as_native_dtype(val)
        if isinstance(paddle_val, paddle.dtype):
            paddle_val = paddle.to_tensor(1, dtype=paddle_val)
        input.append(paddle_val)
    temp_dtype = paddle.add(input[0], input[1]).dtype
    result = paddle.to_tensor(1, dtype=temp_dtype)

    for i in range(2, len(input)):
        temp_dtype = paddle.add(result, input[i]).dtype
        result = paddle.to_tensor(1, dtype=temp_dtype)
    return as_ivy_dtype(result.dtype)


# Extra #
# ------#


def as_ivy_dtype(dtype_in: Union[paddle.dtype, str, bool, int, float], /) -> ivy.Dtype:
    if dtype_in is int:
        return ivy.default_int_dtype()
    if dtype_in is float:
        return ivy.default_float_dtype()
    if dtype_in is complex:
        return ivy.default_complex_dtype()
    if dtype_in is bool:
        return ivy.Dtype("bool")
    if isinstance(dtype_in, str):
        if dtype_in in native_dtype_dict:
            return ivy.Dtype(dtype_in)
        else:
            raise ivy.utils.exceptions.IvyException(
                "Cannot convert to ivy dtype."
                f" {dtype_in} is not supported by Paddle backend."
            )
    return ivy.Dtype(ivy_dtype_dict[dtype_in])


def as_native_dtype(
    dtype_in: Union[paddle.dtype, str, bool, int, float]
) -> paddle.dtype:
    if dtype_in is int:
        return ivy.default_int_dtype(as_native=True)
    if dtype_in is float:
        return ivy.default_float_dtype(as_native=True)
    if dtype_in is complex:
        return ivy.default_complex_dtype(as_native=True)
    if dtype_in is bool:
        return paddle.bool
    if not isinstance(dtype_in, str):
        return dtype_in
    if dtype_in in native_dtype_dict.keys():
        return native_dtype_dict[ivy.Dtype(dtype_in)]
    else:
        raise ivy.utils.exceptions.IvyException(
            "Cannot convert to Paddle dtype." f" {dtype_in} is not supported by Paddle."
        )


def dtype(x: paddle.Tensor, *, as_native: bool = False) -> ivy.Dtype:
    if as_native:
        return ivy.to_native(x).dtype
    return as_ivy_dtype(x.dtype)


def dtype_bits(dtype_in: Union[paddle.dtype, str], /) -> int:
    dtype_str = as_ivy_dtype(dtype_in)
    if "bool" in dtype_str:
        return 1
    return int(
        dtype_str.replace("paddle.", "")
        .replace("uint", "")
        .replace("int", "")
        .replace("bfloat", "")
        .replace("float", "")
        .replace("complex", "")
    )
