# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import traceback

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons.base_report_engine_paper_muncher.engine import PaperMuncher, status

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'
    _description = 'Report Action'

    report_type = fields.Selection(
        selection_add=[('qweb-pdf-paper-muncher', 'PDF (Paper Muncher)')],
        default='qweb-pdf',
        ondelete={'qweb-pdf-paper-muncher': 'set qweb-pdf'}
    )

    @api.model
    def get_pdf_engine_state(self, engine_name=None):
        if engine_name == 'paper-muncher':
            return status
        return super().get_pdf_engine_state(engine_name)

    @api.model
    def _run_paper_muncher(
        self,
        html,
        report_ref=False,
        landscape=False,
    ) -> bytes:
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.
        :param str html: The html to convert to pdf.
        :param report_ref: report reference that is needed to get report paperformat.
        :param landscape: Force the pdf to be rendered under a landscape format.
        :return: Content of the pdf as bytes
        :rtype: bytes
        '''

        report_name = self._get_report(report_ref).report_name or "placeholder_report_title"
        args: list[str] = [report_name, "--httpipe"]
        if landscape:
            args += ['--orientation', 'landscape']

        paperformat_id = self._get_report(report_ref).get_paperformat() if report_ref else self.get_paperformat()
        if paperformat_id:
            if paperformat_id.format and paperformat_id.format != 'custom':
                args += ['--paper', str(paperformat_id.format)]

            if paperformat_id.page_height and paperformat_id.page_width and paperformat_id.format == 'custom':
                args += ['--width', str(paperformat_id.page_width) + 'mm']
                args += ['--height', str(paperformat_id.page_height) + 'mm']

        output, process_error, exception = PaperMuncher(self.env, html, report_name).print(*args)
        if output is None:
            _logger.error(
                'Error while running paper-muncher:\n%s\n%s\n'
                '\nPM\'s process STDERR: %s\n',
                "".join(traceback.format_tb(exception.__traceback__)),
                exception,
                process_error,
            )
            raise UserError(_('The PDF generation failed. Please contact an administrator.'))

        return output, []

    def _run_pdf_engine(self, engine_name, html, report_ref=False, landscape=False):
        if engine_name == 'paper-muncher':
            return self._run_paper_muncher(html, report_ref, landscape)
        return super()._run_pdf_engine(engine_name, html, report_ref, landscape)
