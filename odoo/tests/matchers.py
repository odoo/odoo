import logging
import re
import types
from functools import partial
from typing import TYPE_CHECKING, Any, Self

from lxml import etree

from odoo.libs.debug_log import DebugLog
from odoo.tools import (
    float_compare,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    import odoo.addons.base


_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class RecordCapturer:
    def __init__(self, model: Any, domain: list | None = None) -> None:
        self._model = model
        self._domain = domain or []

    def __enter__(self) -> Self:
        with _debug.perf(
            "test.capture.before",
            cr=self._model.env.cr,
            model=self._model._name,
            domain=len(self._domain),
        ) as span:
            self._before = self._model.search(self._domain, order="id")
            span.set(count=len(self._before))
        self._after: Any = None
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        exc_traceback: types.TracebackType | None,
    ) -> None:
        if exc_type is not None:
            _debug.logic(
                "test.capture.after_skipped",
                model=self._model._name,
                error=exc_type.__name__,
            )
            return
        with _debug.perf(
            "test.capture.after", cr=self._model.env.cr, model=self._model._name
        ) as span:
            self._after = self._model.search(self._domain, order="id") - self._before
            span.set(new=len(self._after))

    @property
    def records(self) -> Any:
        if self._after is None:
            _debug.logic("test.capture.records_recomputed", model=self._model._name)
            return self._model.search(self._domain, order="id") - self._before
        return self._after


def _normalize_arch_for_assert(arch_string: str, parser_method: str = "xml") -> str:
    if parser_method == "xml":
        Parser = etree.XMLParser
    elif parser_method == "html":
        Parser = etree.HTMLParser
    else:
        raise ValueError(
            f"parser_method must be 'xml' or 'html', got {parser_method!r}"
        )
    parser = Parser(remove_blank_text=True)
    _debug.perf.count(
        "test.matchers.normalize_arch", parser=parser_method, size=len(arch_string)
    )
    arch_string = etree.fromstring(arch_string, parser=parser)
    return etree.tostring(arch_string, pretty_print=True, encoding="unicode")


class Like:
    def __init__(self, pattern: str) -> None:
        self.pattern = pattern
        self.regex = ".*".join(
            [re.escape(part.strip()) for part in self.pattern.split("...")]
        )

    __hash__ = None  # type: ignore[assignment]  # unhashable by design

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, str):
            return NotImplemented
        return bool(re.fullmatch(self.regex, other.strip(), re.DOTALL))

    def __repr__(self) -> str:
        return repr(self.pattern)


class WhitespaceInsensitive(str):
    __slots__ = ()

    def __hash__(self) -> int:
        return hash(re.sub(r"\s+", " ", self))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, str):
            return NotImplemented
        return re.sub(r"\s+", " ", self) == re.sub(r"\s+", " ", other)


class Approx:
    def __init__(
        self,
        value: float,
        rounding: float | odoo.addons.base.models.res_currency.ResCurrency,
        /,
        decorate: bool,
    ) -> None:
        self.value = value
        self.decorate = decorate
        self.cmp: Callable[[float, float], int]
        if isinstance(rounding, int):
            self.cmp = partial(float_compare, precision_digits=rounding)
        elif isinstance(rounding, float):
            self.cmp = partial(float_compare, precision_rounding=rounding)
        else:
            self.cmp = rounding.compare_amounts

    def __repr__(self) -> str:
        if self.decorate:
            return f"~{self.value!r}"
        return repr(self.value)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, (float, int)):
            return NotImplemented
        return self.cmp(self.value, other) == 0

    __hash__ = None  # type: ignore[assignment]  # unhashable by design
