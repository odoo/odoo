# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
import re
from collections.abc import Sequence
from contextlib import ExitStack
from typing import Literal
from urllib.parse import urlsplit

import lxml

from odoo import api, fields, models
from odoo.http import request
from odoo.http.session import session_store, update_session_token

from ..paper_muncher import PaperMuncherServer, paper_muncher

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'
    _description = "Report Action"

    report_type = fields.Selection(
        selection_add=[('qweb-pdf-paper-muncher', "PDF (Paper Muncher)")],
        ondelete={'qweb-pdf-paper-muncher': 'set default'},
    )

    def _get_pdf_producer(self, engine_name):
        if engine_name == 'paper-muncher':
            v = paper_muncher().version
            return f"{v}" if v else "Paper Muncher"
        return super()._get_pdf_producer(engine_name)

    @api.model
    def get_pdf_engine_state(self, engine_name):
        if engine_name != 'paper-muncher':
            return super().get_pdf_engine_state(engine_name)
        return paper_muncher().state

    @api.model
    def _run_paper_muncher(
        self,
        bodies: Sequence[str],
        report_ref: str | Literal[False] = False,
        header: str = '',
        footer: str = '',
        landscape: bool = False,
        specific_paperformat_args: dict | None = None,
        scale: int = 72,
    ) -> bytes:
        """Render a PDF from HTML content using Paper Muncher subprocess.

        :param bodies: List of HTML body strings.
        :param report_ref: report reference that is needed to get report paperformat.
        :param header: HTML header fragment.
        :param footer: HTML footer fragment.
        :param landscape: Whether to use landscape layout.
        :param specific_paperformat_args: TODO
        :param scale: document scale (DPI)
        :returns: PDF bytes returned by Paper Muncher.
        :raises RuntimeError: If Paper Muncher fails during any phase.
        """
        if specific_paperformat_args:
            if not landscape and specific_paperformat_args.get('data-report-landscape'):
                landscape = specific_paperformat_args['data-report-landscape']
            if specific_paperformat_args.get('data-report-dpi'):
                scale = int(specific_paperformat_args['data-report-dpi'])

        paperformat = (
            self._get_report(report_ref).get_paperformat()
            if report_ref else
            self.get_paperformat()
        )
        header = header or ''
        footer = footer or ''

        if not isinstance(bodies, (list, tuple)):
            bodies = list(bodies)

        if len(bodies) > 1:
            documents = make_multi_docs_html(bodies, header, footer)
        else:
            header = partition_on_body(header)[1]
            footer = partition_on_body(footer)[1]
            open_body, body, close_body = partition_on_body(bodies[0])
            documents = [f'{open_body}{header}{body}{footer}{close_body}\n']

        names = [f'pipe:/paper-muncher/{i}.html' for i in range(len(documents))]
        extra_args = [
            '--scale', f'{scale}dpi',
            '--margins', 'none',
        ]
        if landscape:
            extra_args += ['--orientation', 'landscape']
        elif paperformat and paperformat.orientation:
            extra_args += ['--orientation', paperformat.orientation.lower()]
        if os.getenv('ODOO_PAPER_MUNCHER_FEATURE') == '1':
            extra_args += ['--feature', '*=on']  # activate all experimental/optional features
        if paperformat and paperformat.format:
            if paperformat.format != 'custom':
                extra_args += ['--paper', paperformat.format]
            elif paperformat.page_height and paperformat.page_width:
                extra_args += ['--width', f'{paperformat.page_width}mm']
                extra_args += ['--height', f'{paperformat.page_height}mm']

        extra_args += ['--debug', 'http-client']
        os_env = os.environ.copy()
        # Disable ANSI color codes in subprocess logs to prevent parsing errors.
        os_env['NO_COLOR'] = '1'

        with (ExitStack() as stack):
            wsgi_environ = {}
            if request and request.db:
                temp_session = session_store().new()
                temp_session.update({
                    **request.session,
                    'debug': '',
                    '_trace_disable': True,
                })
                if temp_session.uid:
                    update_session_token(temp_session, self.env)
                session_store().save(temp_session)
                stack.callback(session_store().delete, temp_session)  # deleted after use
                url = urlsplit(self._get_report_url())
                wsgi_environ['HTTP_HOST'] = url.netloc
                wsgi_environ['HTTP_COOKIE'] = f'session_id={temp_session.sid}; HttpOnly; domain={url.hostname}; path=/;'
            else:
                wsgi_environ['HTTP_X_ODOO_DATABASE'] = self.env.cr.dbname

            with PaperMuncherServer(
                args=[paper_muncher().bin, *names, '-o', 'pipe:/paper-muncher/output.pdf', *extra_args],
                os_env=os_env,
                wsgi_environ=wsgi_environ,
            ) as server:
                return server.serve(documents)

    def _run_pdf_engine_without_processing(
            self,
            engine_name,
            bodies,
            report_ref=False,
            *,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            scale: int = 72,
            **kwargs,
    ) -> bytes:
        if engine_name == 'paper-muncher':
            return self._run_paper_muncher(
                bodies,
                report_ref=report_ref,
                header=header,
                footer=footer,
                landscape=landscape,
                specific_paperformat_args=specific_paperformat_args,
                scale=scale,
            )
        return super()._run_pdf_engine_without_processing(
            engine_name, bodies, report_ref,
            header=header, footer=footer, landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            scale=scale, **kwargs)

    def _run_pdf_engine(
        self,
        engine_name: str,
        html: str,
        report_ref: str | Literal[False] = False,
        landscape: bool = False,
        **kwargs,
    ) -> tuple[bytes, list[int]]:
        if engine_name == 'paper-muncher':
            report_sudo = self._get_report(report_ref).with_context(debug=False)
            bodies, html_ids, header, footer, specific_paperformat_args = (
                report_sudo._prepare_html(html, report_model=report_sudo.model))
            content = self._run_paper_muncher(
                bodies,
                report_ref=report_ref,
                header=header,
                footer=footer,
                landscape=landscape,
                specific_paperformat_args=specific_paperformat_args,
                scale=kwargs.get('dpi-resolution', 72),
            )
            return content, html_ids
        return super()._run_pdf_engine(engine_name, html, report_ref, landscape, **kwargs)


_BODY_TAG_RE = re.compile(r'<body(?:\s[^>]*)?>', re.IGNORECASE)


def partition_on_body(html: str) -> tuple[str, str, str]:
    """
    Get what's before the body, the body and what's after the body.
    When no ``<body>`` was found, it returns ``(html, "", "")``.
    """
    html = str(html)
    m = _BODY_TAG_RE.search(html)
    if not m:
        return html, '', ''
    pre_body = html[:m.end()]
    rest = html[m.end():]
    body, sep, post_body = rest.rpartition('</body>')
    if not sep:
        return html, '', ''
    return pre_body, body, sep + post_body


def make_multi_docs_html(bodies: Sequence[str], header: str = '', footer: str = '') -> Sequence[str]:
    """Inject per-page header/footer fragments into each body HTML document."""

    footer_body = partition_on_body(footer)[1]
    footers = [
        lxml.etree.tostring(f, encoding='unicode')
        for f in (lxml.html.fromstring(footer_body).findall('./div') if footer_body else [])
    ]

    header_body = partition_on_body(header)[1]
    headers = [
        lxml.etree.tostring(h, encoding='unicode')
        for h in (lxml.html.fromstring(header_body).findall('./div') if header_body else [])
    ]

    is_same_length_header = (len(headers) == len(bodies))
    if headers and not is_same_length_header:
        _logger.warning(
            "Header fragments count (%d) does not match body count (%d); reusing the first header fragment where needed.",
            len(headers),
            len(bodies),
        )

    is_same_length_footer = (len(footers) == len(bodies))
    if footers and not is_same_length_footer:
        _logger.warning(
            "Footer fragments count (%d) does not match body count (%d); reusing the first footer fragment where needed.",
            len(footers),
            len(bodies),
        )

    documents = []
    for i, body in enumerate(bodies):
        pre_body, body, post_body = partition_on_body(body)
        header_fragment = headers[i] if is_same_length_header else (headers[0] if headers else '')
        footer_fragment = footers[i] if is_same_length_footer else (footers[0] if footers else '')
        documents.append(f'{pre_body}{header_fragment}{body}{footer_fragment}{post_body}\n')

    return documents
