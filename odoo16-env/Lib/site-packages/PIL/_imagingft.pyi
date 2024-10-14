from typing import Any, TypedDict

from . import _imaging

class _Axis(TypedDict):
    minimum: int | None
    default: int | None
    maximum: int | None
    name: bytes | None

class Font:
    @property
    def family(self) -> str | None: ...
    @property
    def style(self) -> str | None: ...
    @property
    def ascent(self) -> int: ...
    @property
    def descent(self) -> int: ...
    @property
    def height(self) -> int: ...
    @property
    def x_ppem(self) -> int: ...
    @property
    def y_ppem(self) -> int: ...
    @property
    def glyphs(self) -> int: ...
    def render(
        self,
        string: str | bytes,
        fill,
        mode=...,
        dir=...,
        features=...,
        lang=...,
        stroke_width=...,
        anchor=...,
        foreground_ink_long=...,
        x_start=...,
        y_start=...,
        /,
    ) -> tuple[_imaging.ImagingCore, tuple[int, int]]: ...
    def getsize(
        self,
        string: str | bytes | bytearray,
        mode=...,
        dir=...,
        features=...,
        lang=...,
        anchor=...,
        /,
    ) -> tuple[tuple[int, int], tuple[int, int]]: ...
    def getlength(
        self, string: str | bytes, mode=..., dir=..., features=..., lang=..., /
    ) -> float: ...
    def getvarnames(self) -> list[bytes]: ...
    def getvaraxes(self) -> list[_Axis] | None: ...
    def setvarname(self, instance_index: int, /) -> None: ...
    def setvaraxes(self, axes: list[float], /) -> None: ...

def getfont(
    filename: str | bytes,
    size: float,
    index=...,
    encoding=...,
    font_bytes=...,
    layout_engine=...,
) -> Font: ...
def __getattr__(name: str) -> Any: ...
