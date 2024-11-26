from odoo import api, models, fields

papermuncher_state = 'install'


class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[('qweb-pdf-papermuncher', 'PDF (Paper Muncher)')], default='qweb-pdf', ondelete={'qweb-pdf-papermuncher': 'set qweb-pdf'})

    @api.model
    def get_pdf_engine_state(self, engine_name=None):
        """
        Returns the default functional engine, or the requested engine status.

        The state of the pdf engine: install, ok, upgrade, workers or broken.
        * install: Starting state.
        * upgrade: The binary is an older version (< 0.12.0).
        * ok: A binary was found with a recent version (>= 0.12.0).
        * workers: Not enough workers found to perform the pdf rendering process (< 2 workers).
        * broken: A binary was found but not responding.

        :return: engine_name, state
        """
        if engine_name == 'papermuncher':
            return 'papermuncher', papermuncher_state
        engine, state = super().get_pdf_engine_state(engine_name)
        if engine_name or state == 'ok':
            return engine, state
        if papermuncher_state == 'ok':
            return 'papermuncher', 'ok'
        return engine, state

    @api.model
    def _run_papermuncher(
            self,
            bodies,
            report_ref=False,
            header=None,
            footer=None,
            landscape=False,
            specific_paperformat_args=None,
            set_viewport_size=False) -> bytes:
        '''Execute wkhtmltopdf as a subprocess in order to convert html given in input into a pdf
        document.

        :param list[str] bodies: The html bodies of the report, one per page.
        :param report_ref: report reference that is needed to get report paperformat.
        :param str header: The html header of the report containing all headers.
        :param str footer: The html footer of the report containing all footers.
        :param landscape: Force the pdf to be rendered under a landscape format.
        :param specific_paperformat_args: dict of prioritized paperformat arguments.
        :param set_viewport_size: Enable a viewport sized '1024x1280' or '1280x1024' depending of landscape arg.
        :return: Content of the pdf as bytes
        :rtype: bytes
        '''

        raise NotImplementedError
