from odoo import fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    l10n_jo_edi_pos_is_needed = fields.Boolean()
    l10n_jo_edi_pos_state = fields.Selection(
        selection=[('error', 'Error'), ('sent', 'Sent')],
        string="JoFotara Receipt State",
        tracking=True,
        copy=False,
    )
    l10n_jo_edi_pos_error = fields.Text(
        string="JoFotara Error",
        copy=False,
        readonly=True,
    )

    def button_l10n_jo_edi_pos(self):
        return

    def _l10n_jo_qr_code_src(self):
        return
