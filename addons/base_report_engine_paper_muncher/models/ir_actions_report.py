# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging

from odoo import api, models, fields, _
from odoo.exceptions import UserError
from odoo.addons.base_report_engine_paper_muncher.engine.paper_muncher import run_paper_muncher
from odoo.addons.base_report_engine_paper_muncher.engine import status

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
        if engine_name is None:
            if self.report_type.startswith('qweb-pdf-paper-muncher'):
                engine_name = 'paper-muncher'
        if engine_name == 'paper-muncher':
            return status
        return super().get_pdf_engine_state(engine_name)

    @api.model
    def _run_paper_muncher(
        self,
        bodies,
        report_ref=False,
        landscape=False,
        header=None,
        footer=None,
        specific_paperformat_args=None,
        set_viewport_size=False,
    ) -> bytes:
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.
        :param str html: The html to convert to pdf.
        :param report_ref: report reference that is needed to get report paperformat.
        :param landscape: Force the pdf to be rendered under a landscape format.
        :return: Content of the pdf as bytes
        :rtype: bytes, list
        '''

        paperformat_id = self._get_report(report_ref).get_paperformat() if report_ref else self.get_paperformat()

        try:
            output = run_paper_muncher(
                paperformat_id,
                bodies,
                header=header,
                footer=footer,
                landscape=landscape,
                specific_paperformat_args=specific_paperformat_args,
                set_viewport_size=set_viewport_size
            )
        except Exception as e:  # noqa: BLE001
            _logger.error(
                "Error while running paper-muncher",
                exc_info=e,
            )
            raise UserError(_('The PDF generation failed. Please contact an administrator.'))

        return output

    def _run_pdf_engine(self, engine_name, html, report_ref=False, landscape=False, **kwargs):
        if engine_name == 'paper-muncher':
            report_sudo = self._get_report(report_ref)
            bodies, html_ids, header, footer, specific_paperformat_args = report_sudo \
                .with_context(debug=False)._prepare_wkhtmltopdf_html(html, report_model=report_sudo.model)
            content =  self._run_paper_muncher(bodies,
                   report_ref=report_ref,
                   header=header,
                   footer=footer,
                   landscape=landscape,
                   specific_paperformat_args=specific_paperformat_args)
            return content, html_ids
        return super()._run_pdf_engine(engine_name, html, report_ref, landscape)
