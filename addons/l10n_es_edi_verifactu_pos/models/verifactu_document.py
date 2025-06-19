import contextlib

from odoo import fields, models
from odoo.exceptions import UserError


class L10nEsEdiVerifactuDocument(models.Model):
    _inherit = 'l10n_es_edi_verifactu.document'

    pos_order_id = fields.Many2one(
        string="PoS Order",
        comodel_name='pos.order',
        readonly=True,
    )

    def _post_send_hook(self, info):
        super()._post_send_hook(info)
        for document in self:
            order = document.pos_order_id
            if order.l10n_es_edi_verifactu_state == 'cancelled' and order.state != 'cancel':
                with contextlib.suppress(UserError):
                    order.action_pos_order_cancel()
