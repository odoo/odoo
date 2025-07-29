import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class L10nEsEdiVerifactuDocument(models.Model):
    _inherit = 'l10n_es_edi_verifactu.document'

    pos_order_id = fields.Many2one(
        string="PoS Order",
        comodel_name='pos.order',
        readonly=True,
    )

    def _cancel_after_sending(self, info):
        super()._cancel_after_sending(info)
        for document in self:
            order = document.pos_order_id
            if order.l10n_es_edi_verifactu_state == 'cancelled' and order.state != 'cancel':
                try:
                    order.action_pos_order_cancel()
                except UserError as error:
                    _logger.error("Error while canceling order %(name)s (id %(record_id)s) after Veri*Factu cancellation:\n%(error)s",
                                  record_id=order.id, name=order.name, error=error)
