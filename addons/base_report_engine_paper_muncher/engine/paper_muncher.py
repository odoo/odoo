# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import re

import subprocess
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from email.utils import format_datetime
from itertools import count
from typing import Optional
from lxml import etree, html
from PyPDF2 import PdfMerger
import inspect

import odoo

try:
    import magic
except ImportError:
    magic = None

from .communication import write_with_timeout, read_paper_muncher_request, partition_on_body, consume_paper_muncher_request, read_all_with_timeout, make_multi_docs_html, generate_odoo_http_response
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

    # hack for general ledger
    fname = str(inspect.stack()[2].function)
    if fname  == "_render_qweb_pdf_prepare_streams":
        extra_args = ['--scale', '72dpi']
    elif fname == "export_to_pdf":
        extra_args = ['--scale', '50dpi']
    else:
        extra_args = []

    if landscape:
        extra_args += ['--orientation', 'landscape']

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

    # hack for multi body
    if len(bodies) == 1:
        return run_process(binary, extra_args, documents[0])
    return run_process_multi(binary, extra_args, documents)

    #merger = PdfMerger()
    #for content in documents:
    #    pdf_bytes = run_process(binary, extra_args, content)
    #    merger.append(BytesIO(pdf_bytes))
    #output = BytesIO()
    #merger.write(output)
    #merger.close()

    #return output.getvalue()


def run_process_multi(
        binary,
        extra_args,
        documents,
):
    names = [f"pipe:{i}.html" for i in range(len(documents))]
    with subprocess.Popen(
            [binary, "print", *names, '-o', "pipe:" ] + extra_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
    ) as process:
        for request_no in count(start=1):
            try:
                path = read_paper_muncher_request(process.stdout)
            except (EOFError, TimeoutError):
                process.kill()
                process.wait()
                raise

            if path is None:
                break

            # if match with format /{i}.html it's a document request and get the i
            is_document = re.match(r'^/(\d+).html$', path)
            if is_document:
                index = int(is_document.group(1))
                content = documents[index]
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
                                       b'date':  format_datetime(now, usegmt=True).encode(),
                                       b'server': SERVER_SOFTWARE.encode(),
                                   }
                write_with_timeout(process.stdin, response_headers)
                write_with_timeout(process.stdin, content.encode())
                process.stdin.flush()
            else:
                for chunk in generate_odoo_http_response(path):
                    write_with_timeout(process.stdin, chunk)
                process.stdin.flush()

            if process.poll() is not None:
                raise RuntimeError(
                    "Paper Muncher crashed while serving asset"
                    f" {request_no}: {path}"
                )

        now = datetime.now(timezone.utc)
        final_response = (
                             b"HTTP/1.1 200 OK\r\n"
                             b"Date: %(date)s\r\n"
                             b"Server: %(server)s\r\n"
                             b"\r\n"
                         ) % {
                             b'date': format_datetime(now, usegmt=True).encode(),
                             b'server': SERVER_SOFTWARE.encode(),
                         }

        write_with_timeout(process.stdin, final_response)
        process.stdin.flush()
        process.stdin.close()

        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before returning PDF")

        try:
            rendered_content = read_all_with_timeout(process.stdout)
            stderr_output = read_all_with_timeout(process.stderr)
        except (EOFError, TimeoutError):
            process.kill()
            process.wait()
            raise

        if stderr_output:
            _logger.warning(
                "Paper Muncher error output: %s",
                stderr_output.decode('utf-8', errors='replace'),
            )

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            _logger.warning(
                "Paper Muncher did not terminate in time,"
                "forcefully killed it"
            )

        if process.returncode != 0:
            _logger.warning(
                "Paper Muncher exited with code %d",
                process.returncode,
            )

        if not rendered_content.startswith(b'%PDF-'):
            raise RuntimeError(
                "Paper Muncher did not return valid PDF content"
            )

        return rendered_content


def run_process(
        binary,
        extra_args,
        content,
):
    with subprocess.Popen(
            [binary, "print", "pipe:", '-o', "pipe:"] + extra_args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
    ) as process:
        # Phase 1: send HTML content headers and body
        try:
            consume_paper_muncher_request(process.stdout)
        except EOFError as early_eof:
            raise RuntimeError(
                "Paper Muncher terminated prematurely (phase 1)"
            ) from early_eof

        if process.poll() is not None:
            raise RuntimeError(
                "Paper Muncher crashed before receiving content")

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
                               b'date':  format_datetime(now, usegmt=True).encode(),
                               b'server': SERVER_SOFTWARE.encode(),
                           }

        write_with_timeout(process.stdin, response_headers)
        write_with_timeout(process.stdin, content.encode())
        process.stdin.flush()

        if process.poll() is not None:
            raise RuntimeError(
                "Paper Muncher crashed while sending HTML content")

        # Phase 2: serve asset requests until the pdf is ready
        for request_no in count(start=1):
            try:
                path = read_paper_muncher_request(process.stdout)
            except (EOFError, TimeoutError):
                process.kill()
                process.wait()
                raise

            if path is None:
                break

            for chunk in generate_odoo_http_response(path):
                write_with_timeout(process.stdin, chunk)
            process.stdin.flush()

            if process.poll() is not None:
                raise RuntimeError(
                    "Paper Muncher crashed while serving asset"
                    f" {request_no}: {path}"
                )

        # Phase 3: send final OK and read PDF bytes
        now = datetime.now(timezone.utc)
        final_response = (
                             b"HTTP/1.1 200 OK\r\n"
                             b"Date: %(date)s\r\n"
                             b"Server: %(server)s\r\n"
                             b"\r\n"
                         ) % {
                             b'date': format_datetime(now, usegmt=True).encode(),
                             b'server': SERVER_SOFTWARE.encode(),
                         }

        write_with_timeout(process.stdin, final_response)
        process.stdin.flush()
        process.stdin.close()

        if process.poll() is not None:
            raise RuntimeError("Paper Muncher crashed before returning PDF")

        try:
            rendered_content = read_all_with_timeout(process.stdout)
            stderr_output = read_all_with_timeout(process.stderr)
        except (EOFError, TimeoutError):
            process.kill()
            process.wait()
            raise

        if stderr_output:
            _logger.warning(
                "Paper Muncher error output: %s",
                stderr_output.decode('utf-8', errors='replace'),
            )

        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            _logger.warning(
                "Paper Muncher did not terminate in time,"
                "forcefully killed it"
            )

        if process.returncode != 0:
            _logger.warning(
                "Paper Muncher exited with code %d",
                process.returncode,
            )

        if not rendered_content.startswith(b'%PDF-'):
            raise RuntimeError(
                "Paper Muncher did not return valid PDF content"
            )

        return rendered_content
