from odoo import models, fields, _
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    arba_cit = fields.Char(
        related='company_id.arba_cit',
        readonly=False,
    )

    def l10n_ar_arba_cit_test(self):
        self.ensure_one()
        cuit = self.company_id.partner_id.ensure_vat()
        _logger.info('Getting ARBA data for cuit %s' % (cuit))
        try:
            ws = self.company_id.arba_connect()
            ws.ConsultarContribuyentes(
                fields.Date.start_of(fields.Date.today(), 'month').strftime('%Y%m%d'),
                fields.Date.end_of(fields.Date.today(), 'month').strftime('%Y%m%d'),
                cuit)
        except Exception as exp:
            raise UserError(_('No se pudo conectar a ARBA: %s') % str(exp))

        if ws.CodigoError:
            self.company_id._process_message_error(ws)
        raise UserError(_('La conexión ha sido exitosa'))
