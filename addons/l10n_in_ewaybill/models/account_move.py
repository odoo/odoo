# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = 'account.move'

    l10n_in_ewaybill_ids = fields.One2many(
        'l10n.in.ewaybill',
        'account_move_id',
        string="E-Waybill",
        readonly=True
    )
    l10n_in_ewaybill_name = fields.Char(
        "Indian Ewaybill Number",
        compute='_compute_l10n_in_ewaybill_details'
    )
    l10n_in_ewaybill_expiry_date = fields.Datetime(compute='_compute_l10n_in_ewaybill_details')
    l10n_in_ewaybill_feature_enabled = fields.Boolean(string="E-Waybill Feature Enabled", related='company_id.l10n_in_ewaybill_feature')

    def _get_l10n_in_ewaybill_form_action(self):
        return self.env.ref('l10n_in_ewaybill.l10n_in_ewaybill_form_action')._get_action_dict()

    def action_l10n_in_ewaybill_create(self):
        self.ensure_one()
        if self.l10n_in_ewaybill_ids:
            raise UserError(_("Ewaybill already created for this move."))
        action = self._get_l10n_in_ewaybill_form_action()
        action['context'] = {'default_account_move_id': self.id}
        return action

    def action_open_l10n_in_ewaybill(self):
        self.ensure_one()
        action = self._get_l10n_in_ewaybill_form_action()
        action['res_id'] = self.l10n_in_ewaybill_ids and self.l10n_in_ewaybill_ids[0].id
        return action

    @api.depends('l10n_in_ewaybill_ids.state')
    def _compute_l10n_in_ewaybill_details(self):
        for move in self:
            ewaybill = move.l10n_in_ewaybill_ids and move.l10n_in_ewaybill_ids[0]
            if move.country_code == 'IN' and move.company_id.l10n_in_ewaybill_feature and ewaybill.state == 'generated':
                move.l10n_in_ewaybill_name = ewaybill.name
                move.l10n_in_ewaybill_expiry_date = ewaybill.ewaybill_expiry_date
            else:
                move.l10n_in_ewaybill_name = False
                move.l10n_in_ewaybill_expiry_date = False
