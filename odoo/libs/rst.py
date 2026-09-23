from __future__ import annotations

import io
import typing

from docutils import nodes
from docutils.core import publish_string
from docutils.transforms import Transform, writer_aux
from docutils.writers.html4css1 import Writer

__all__ = [
    "SAFE_SETTINGS",
    "render_html",
]

SAFE_SETTINGS: typing.Final[dict[str, typing.Any]] = {
    "report_level": 3,
    "halt_level": 5,
    "raw_enabled": False,
    "file_insertion_enabled": False,
}


class _DropSystemMessages(Transform):
    default_priority = 870

    def apply(self) -> None:
        for node in list(self.document.findall(nodes.system_message)):
            node.parent.remove(node)


class _HtmlDocumentWriter(Writer):
    def get_transforms(self) -> list[type[Transform]]:
        return [_DropSystemMessages, writer_aux.Admonitions]


def render_html(source: str) -> tuple[str, str]:
    warnings = io.StringIO()
    html = publish_string(
        source=source,
        writer=_HtmlDocumentWriter(),
        settings_overrides={
            **SAFE_SETTINGS,
            "embed_stylesheet": False,
            "doctitle_xform": False,
            "output_encoding": "unicode",
            "xml_declaration": False,
            "warning_stream": warnings,
        },
    )
    return html, warnings.getvalue().strip()
