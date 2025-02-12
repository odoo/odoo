import logging
import subprocess
from odoo import api, models, fields
from odoo.tools.misc import find_in_path
from odoo.exceptions import UserError
from odoo import _, api

from .papermuncher import printPM, OdooLoader

_logger = logging.getLogger(__name__)
papermuncher_state = 'install'

def _get_paper_muncher_bin():
    return find_in_path('paper-muncher')


try:
    process = subprocess.Popen(
        [_get_paper_muncher_bin(), '--usage'], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
except (OSError, IOError):
    _logger.info('You need \'paper-muncher\' to print a pdf version of the reports.')
    papermuncher_state = 'broken'
else:
    _logger.info(f'Will use the \'paper-muncher\' binary at {_get_paper_muncher_bin()}')
    papermuncher_state = 'ok'

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    report_type = fields.Selection(selection_add=[('qweb-pdf-papermuncher', 'PDF (Paper Muncher)')], default='qweb-pdf', ondelete={'qweb-pdf-papermuncher': 'set qweb-pdf'})

    @api.model
    def get_pdf_engine_state(self, engine_name=None):
        if engine_name == 'papermuncher':
            return 'papermuncher', papermuncher_state
        return super().get_pdf_engine_state(engine_name)

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

        if len(bodies) != 1:
            raise ValueError('Paper Muncher only supports one body per report')

        body = bodies[0]

        odooLoader = OdooLoader(self.env, body, report_name)

        output, procStderr, exc = printPM(odooLoader, _get_paper_muncher_bin(), *args)

        if output is None:
            import traceback
            raise UserError(
                f'Error while running paper-muncher:\n{"".join(traceback.format_tb(exc.__traceback__))}\n{exc}\n'
                f'\nPM\'s process STDERR: {procStderr}\n')

        return output
