# Part of Odoo. See LICENSE file for full copyright and licensing details.

import io
import itertools
import logging
import os
from collections.abc import Sequence
from contextlib import ExitStack, closing
from urllib.parse import urlsplit

from odoo import api, fields, models
from odoo.http import request
from odoo.http.session import session_store, update_session_token

from odoo.addons.base.models.ir_actions_report import ReportDocument, ReportPageSetup
from odoo.addons.base_report_paper_muncher.paper_muncher import (
    PaperMuncherServer,
    paper_muncher,
)

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
    def _run_paper_muncher(self, documents: Sequence[ReportDocument], page_setup: ReportPageSetup) -> bytes:
        """Render documents with one Paper Muncher subprocess.

        :param documents: documents to concatenate, with the same decorations
            unless paper-muncher has the ``per-input-decoration`` capability.
        :param page_setup: Resolved page setup. The top and bottom margins are
            mapped to the header and footer sizes; ``header_spacing`` and
            ``header_line`` are not supported.
        :returns: PDF bytes returned by Paper Muncher.
        :raises RuntimeError: If Paper Muncher fails during any phase.
        """
        assert isinstance(self, IrActionsReport)
        per_input_decoration = paper_muncher().has_capability('per-input-decoration')

        # documents sharing a decoration share its index
        headers = {html: i for i, html in enumerate(dict.fromkeys(d.header for d in documents if d.header))}
        footers = {html: i for i, html in enumerate(dict.fromkeys(d.footer for d in documents if d.footer))}

        inputs = []
        for i, document in enumerate(documents):
            inputs.append(f'pipe:/paper-muncher/{i}.html')
            if i and not per_input_decoration:
                # older binaries apply the decorations to every input
                continue
            if document.header:
                inputs += ['--header', f'pipe:/paper-muncher/header-{headers[document.header]}.html']
            if document.footer:
                inputs += ['--footer', f'pipe:/paper-muncher/footer-{footers[document.footer]}.html']

        # wkhtmltopdf lays CSS px out at ~76/dpi with smart shrinking, and at its
        # zoom (96/dpi) with --disable-smart-shrinking; it defaults to 96 dpi.
        scale = (96 if page_setup.disable_shrinking else 76) / (page_setup.dpi or 96)

        extra_args = [
            '--scale', f'{scale}x',
            '--margins', f'0mm {page_setup.margin_right:g}mm 0mm {page_setup.margin_left:g}mm',
            '--header-size', f'{page_setup.margin_top:g}mm',
            '--footer-size', f'{page_setup.margin_bottom:g}mm',
            '--orientation', 'landscape' if page_setup.landscape else 'portrait',
            '--sandboxed',
        ]

        features = []
        if os.getenv('ODOO_PAPER_MUNCHER_FEATURE') == '1':
            features.append('*=on')  # activate all experimental/optional features
        else:
            features += [f'{feature}=on' for feature in paper_muncher().features]
        if features:
            # NOTE: a single --feature option, repeating it would override the previous one
            extra_args += ['--feature', *features]
        if page_setup.paper_format:
            extra_args += ['--paper', page_setup.paper_format]
        elif page_setup.page_width and page_setup.page_height:
            extra_args += ['--width', f'{page_setup.page_width:g}mm']
            extra_args += ['--height', f'{page_setup.page_height:g}mm']

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
                args=[paper_muncher().bin, *inputs, '-o', 'pipe:/paper-muncher/output.pdf', *extra_args],
                os_env=os_env,
                wsgi_environ=wsgi_environ,
            ) as server:
                return server.serve(  # TODO: ir.config_parameter
                    [document.body for document in documents], list(headers), list(footers))

    def _run_pdf_engine_with_documents(self, engine_name, documents, page_setup, **kwargs) -> bytes:
        if engine_name != 'paper-muncher':
            return super()._run_pdf_engine_with_documents(engine_name, documents, page_setup, **kwargs)
        if paper_muncher().has_capability('per-input-decoration'):
            return self._run_paper_muncher(documents, page_setup)
        # Older binaries apply the decorations to every input: one subprocess
        # per run of documents with the same decorations.
        pdfs = [
            self._run_paper_muncher(list(batch), page_setup)
            for _decorations, batch in itertools.groupby(documents, key=lambda document: (document.header, document.footer))
        ]
        if len(pdfs) == 1:
            return pdfs[0]
        with closing(self._merge_pdfs([io.BytesIO(pdf) for pdf in pdfs])) as stream:
            return stream.getvalue()
