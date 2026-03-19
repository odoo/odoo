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

    if len(bodies) == 1:
        return run_process(binary, extra_args, documents[0])
    return run_process_multi(binary, extra_args, documents)


def run_process_multi(
        binary,
        extra_args,
        documents,
):
    names = [f"pipe:{i}.html" for i in range(len(documents))]
    _logger.info("=== run_process_multi START ===")
    _logger.info("Documents count: %d", len(documents))
    _logger.info("Names: %s", names)
    _logger.info("Binary: %s", binary)
    _logger.info("Extra args: %s", extra_args)

    env = os.environ.copy()
    # Disable ANSI color codes in subprocess logs to prevent parsing errors.
    env['NO_COLOR'] = '1'

    for i, doc in enumerate(documents):
        doc_preview = doc[:200] if len(doc) > 200 else doc
        _logger.info("Document[%d]: %d bytes, preview: %r", i, len(doc), doc_preview)

    command = [binary, *names, '-o', "pipe:"] + extra_args
    _logger.info("Full command: %s", ' '.join(command))

    with subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
    ) as process:
        _logger.info("Paper Muncher process started: pid=%d", process.pid)
        try:
            _serve_requests(process, documents)
            # Multi-document mode: Paper Muncher doesn't send PUT request
            # Just close stdin and read the PDF
            _logger.info("Closing stdin to signal end of input")
            process.stdin.close()

            if process.poll() is not None:
                raise RuntimeError("Paper Muncher crashed before returning PDF")

            try:
                rendered_content = read_all_with_timeout(process.stdout)
                stderr_output = read_all_with_timeout(process.stderr)
            except (EOFError, TimeoutError):
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    process.wait()
                except Exception:
                    pass
                raise

            if stderr_output:
                _logger.warning(
                    "Paper Muncher error output: %s",
                    stderr_output.decode('utf-8', errors='replace'),
                )

            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    process.kill()
                except Exception:
                    pass
                try:
                    process.wait()
                except Exception:
                    pass
                _logger.warning(
                    "Paper Muncher did not terminate in time, forcefully killed it"
                )

            if process.returncode != 0:
                _logger.warning("Paper Muncher exited with code %d", process.returncode)

            if not rendered_content.startswith(b'%PDF-'):
                raise RuntimeError("Paper Muncher did not return valid PDF content")

            _logger.info("=== run_process_multi SUCCESS ===")
            return rendered_content
        except Exception as e:
            _logger.error("=== run_process_multi FAILED: %s ===", e, exc_info=True)
            raise


def run_process(
        binary,
        extra_args,
        content,
):
    env = os.environ.copy()
    # Disable ANSI color codes in subprocess logs to prevent parsing errors.
    env['NO_COLOR'] = '1'

    with subprocess.Popen(
            [binary, "pipe:", '-o', "pipe:"] + extra_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
    ) as process:
        try:
            consume_paper_muncher_request(process.stdout)
        except EOFError as early_eof:
            raise RuntimeError("Paper Muncher terminated prematurely (phase 1)") from early_eof

        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before receiving content")

        now = datetime.now(timezone.utc)
        response_headers = (
                               b"HTTP/1.1 200 OK\r\n"
                               b"Content-Length: %(length)d\r\n"
                               b"Content-Type: text/html\r\n"
                               b"Date: %(date)s\r\n"
                               b"Server: %(server)s\r\n"
                               b"\r\n"
                           ) % {
                               b'length': len(content.encode()),
                               b'date': format_datetime(now, usegmt=True).encode(),
                               b'server': SERVER_SOFTWARE.encode(),
                           }

        try:
            _safe_write(process, response_headers)
            _safe_write(process, content.encode())
            process.stdin.flush()
        except TimeoutError:
            raise

        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed while sending HTML content")

        return _serve_requests(process, [content])

