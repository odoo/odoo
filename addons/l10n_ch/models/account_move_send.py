from odoo import _, api, fields, models


class AccountMoveSend(models.TransientModel):
    _inherit = 'account.move.send'

    partners_without_street = fields.One2many('res.partner', compute='_compute_partners_without_street')

    @api.depends('move_ids.partner_id.street', 'move_ids.partner_id.street2')
    def _compute_partners_without_street(self):
        for wizard in self:
            wizard.partners_without_street = (
                self.env.company.qr_code
                and wizard.move_ids.partner_id.filtered(lambda partner: not partner.street and not partner.street2)
            )

    def action_view_street_missing_partners(self):
        self.ensure_one()
        return self.partners_without_street._get_records_action(name=_("Check Partner(s)"))
