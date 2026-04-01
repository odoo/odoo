# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

import subprocess
import os
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from email.utils import format_datetime
from typing import Optional
from lxml import etree, html
from PyPDF2 import PdfMerger
import inspect

import odoo

try:
    import magic
except ImportError:
    magic = None

from .communication import (partition_on_body, consume_paper_muncher_request, read_all_with_timeout, make_multi_docs_html,
                            _serve_requests, _safe_write)
from .utils import get_paper_muncher_binary

_logger = logging.getLogger(__name__)

SERVER_SOFTWARE = f'{odoo.release.product_name}/{odoo.release.version}'

def run_paper_muncher(
        paperformat,
        bodies: Sequence[str],
        header: str = '',
        footer: str = '',
        landscape: bool = False,
        specific_paperformat_args: Optional[Mapping] = None,
        set_viewport_size: Optional[str] = None,
) -> bytes:
    """Render a PDF from HTML content using Paper Muncher subprocess.

    :param paperformat: Odoo report paperformat object (may have format, width/height).
    :param Sequence[str] bodies: List of HTML body strings.
    :param str header: HTML header fragment.
    :param str footer: HTML footer fragment.
    :param bool landscape: Whether to use landscape layout.
    :param Optional[Mapping] specific_paperformat_args: Optional override arguments.
    :param Optional[str] set_viewport_size: Optional viewport string (currently unused).
    :return: PDF bytes returned by Paper Muncher.
    :rtype: bytes
    :raises RuntimeError: If Paper Muncher fails during any phase.
    """


    if not isinstance(bodies, (list, tuple)):
        bodies = list(bodies)


    if len(bodies) > 1:
        documents = make_multi_docs_html(bodies, header, footer)
    else:
        header = partition_on_body(header)[1]
        footer = partition_on_body(footer)[1]
        open_body, body, close_body = partition_on_body(bodies[0])
        documents = ["".join((open_body, header, body, footer, close_body, "\n"))]

    FEATURE_FLAGS = True


    # hack for general ledger
    fname = str(inspect.stack()[2].function)
    if fname  == "_render_qweb_pdf_prepare_streams":
        extra_args = ['--scale', '72dpi']
    elif fname == "export_to_pdf":
        extra_args = ['--scale', '72dpi']
    else:
        extra_args = []

    if landscape:
        extra_args += ['--orientation', 'landscape']

    if FEATURE_FLAGS:
        extra_args += ['--feature', '*=on']
        extra_args += ['--debug', 'http-client=on']
        extra_args += ['--margins', 'none']

    if paperformat and paperformat.format:
        if paperformat.format != 'custom':
            extra_args += ['--paper', str(paperformat.format)]
        elif paperformat.page_height and paperformat.page_width:
            extra_args += ['--width', f'{paperformat.page_width}mm']
            extra_args += ['--height', f'{paperformat.page_height}mm']

    if not (binary := get_paper_muncher_binary()):
        raise RuntimeError(
            "Paper Muncher binary not found or not usable. "
            "Ensure it is installed and available in the system PATH."
        )

    return run_process(binary, extra_args, documents)


def run_process(
        binary,
        extra_args,
        documents,
):
    env = os.environ.copy()
    # Disable ANSI color codes in subprocess logs to prevent parsing errors.
    env['NO_COLOR'] = '1'

    names = [f"pipe:{i}.html" for i in range(len(documents))]

    with subprocess.Popen(
            [binary, *names, '-o', "pipe:"] + extra_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
    ) as process:
        return _serve_requests(process, documents)

