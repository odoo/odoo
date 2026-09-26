# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import os
from collections.abc import Sequence
from contextlib import ExitStack
from typing import Literal
from urllib.parse import urlsplit

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
    ) -> bytes:
        """Render a PDF from HTML content using Paper Muncher subprocess.

        :param bodies: List of HTML body strings.
        :param report_ref: report reference that is needed to get report paperformat.
        :param header: HTML header fragment.
        :param footer: HTML footer fragment.
        :param landscape: Whether to use landscape layout.
        :param specific_paperformat_args: A dictionary containing specific paperformat
            arguments that override the default paperformat settings. Supported keys:

            ``data-report-dpi``
                DPI used to compute the document scale, overrides ``paperformat.dpi``.
            ``data-report-margin-top``
                top margin in mm, mapped to the header size, overrides
                ``paperformat.margin_top``.
            ``data-report-margin-bottom``
                bottom margin in mm, mapped to the footer size, overrides
                ``paperformat.margin_bottom``.
            ``data-report-landscape``
                force landscape orientation; combined with the ``landscape`` parameter,
                either one being truthy is enough.

            Any other key is ignored.
        :returns: PDF bytes returned by Paper Muncher.
        :raises RuntimeError: If Paper Muncher fails during any phase.
        """
        specific_paperformat_args = specific_paperformat_args or {}
        paperformat = (
            self._get_report(report_ref).get_paperformat()
            if report_ref else
            self.get_paperformat()
        )

        if not isinstance(bodies, (list, tuple)):
            bodies = list(bodies)

        names = [f'pipe:/paper-muncher/{i}.html' for i in range(len(bodies))]
        extra_args = [
            '--scale', f'{76 / float(specific_paperformat_args.get('data-report-dpi', paperformat.dpi))}x',
            '--margins', f'0mm {paperformat.margin_right}mm 0mm {paperformat.margin_left}mm',
            '--header-size', f'{specific_paperformat_args.get('data-report-margin-top', paperformat.margin_top)}mm',
            '--footer-size', f'{specific_paperformat_args.get('data-report-margin-bottom', paperformat.margin_bottom)}mm',
        ]

        if header:
            extra_args += ['--header', 'pipe:/paper-muncher/header.html']

        if footer:
            extra_args += ['--footer', 'pipe:/paper-muncher/footer.html']

        if landscape or specific_paperformat_args.get('data-report-landscape', False):
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
                args=[paper_muncher().bin, *names, '-o', 'pipe:/paper-muncher/output.pdf', '--sandboxed', *extra_args],
                os_env=os_env,
                wsgi_environ=wsgi_environ,
            ) as server:
                return server.serve(bodies, header, footer)  # TODO: ir.config_parameter

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
            )
        return super()._run_pdf_engine_without_processing(
            engine_name, bodies, report_ref,
            header=header, footer=footer, landscape=landscape,
            specific_paperformat_args=specific_paperformat_args,
            **kwargs)

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
            )
            return content, html_ids
        return super()._run_pdf_engine(engine_name, html, report_ref, landscape, **kwargs)
