"""Collection of Jax network layers, wrapped to fit Ivy syntax and signature."""

# global
import jax.lax as jlax

# local
from ivy.functional.backends.jax import JaxArray
from typing import Union, Tuple, Sequence


def conv1d(
    x: JaxArray,
    filters: JaxArray,
    strides: int,
    padding: str,
    data_format: str = "NWC",
    dilations: int = 1,
) -> JaxArray:
    strides = (strides,) if isinstance(strides, int) else strides
    dilations = (dilations,) if isinstance(dilations, int) else dilations
    return jlax.conv_general_dilated(
        x, filters, strides, padding, None, dilations, (data_format, "WIO", data_format)
    )


def conv1d_transpose(*_):
    raise Exception("Convolutions not yet implemented for jax library")


def conv2d(
    x: JaxArray,
    filters: JaxArray,
    strides: Union[int, Tuple[int, int]],
    padding: str,
    data_format: str = "NHWC",
    dilations: int = 1,
) -> JaxArray:
    strides = [strides] * 2 if isinstance(strides, int) else strides
    dilations = [dilations] * 2 if isinstance(dilations, int) else dilations
    return jlax.conv_general_dilated(
        x,
        filters,
        strides,
        padding,
        None,
        dilations,
        (data_format, "HWIO", data_format),
    )


def depthwise_conv2d(*_):
    raise Exception("Convolutions not yet implemented for jax library")


def conv2d_transpose(*_):
    raise Exception("Convolutions not yet implemented for jax library")


def conv3d(*_):
    raise Exception("Convolutions not yet implemented for jax library")


def conv3d_transpose(
    x: JaxArray,
    filters: JaxArray,
    strides: Union[int, Tuple[int], Tuple[int, int], Tuple[int, int, int]],
    padding: Union[str, Sequence[Tuple[int, int]]],
    dilations: Union[int, Tuple[int], Tuple[int, int], Tuple[int, int, int]] = 1,
    data_format: str = "NDHWC",
) -> JaxArray:
    strides = [strides] * 3 if isinstance(strides, int) else strides
    dilations = [dilations] * 3 if isinstance(dilations, int) else dilations
    dimension_numbers = (data_format, "HWDIO", data_format)
    res = jlax.conv_transpose(
        x, filters, strides, padding, dilations, dimension_numbers
    )
    return res
