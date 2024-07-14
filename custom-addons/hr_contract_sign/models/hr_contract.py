# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class HrContract(models.Model):
    _name = 'hr.contract'
    _inherit = 'hr.contract'

    sign_request_ids = fields.Many2many('sign.request', string='Requested Signatures')
    sign_request_count = fields.Integer(compute='_compute_sign_request_count')

    def write(self, vals):
        res = super().write(vals)
        if vals.get('state') == 'cancel':
            open_request_ids = self.sign_request_ids.filtered_domain([('state', '=', 'sent')])
            open_request_ids.cancel()
            for sign_request in open_request_ids:
                sign_request.message_post(body=_("This sign request has been canceled due to the cancellation of the related contract."))
        return res

    @api.depends('sign_request_ids')
    def _compute_sign_request_count(self):
        for contract in self:
            contract.sign_request_count = len(contract.sign_request_ids)

    @api.ondelete(at_uninstall=False)
    def _unlink_if_sign_request_canceled(self):
        if self.sign_request_ids.filtered(lambda s: s.state != 'canceled'):
            raise ValidationError(_(
                "You can't delete a contract linked to a signed document, archive it instead."))

    def open_sign_requests(self):
        self.ensure_one()
        if len(self.sign_request_ids.ids) == 1:
            return self.sign_request_ids.go_to_document()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Signature Requests',
            'view_mode': 'kanban,tree',
            'res_model': 'sign.request',
            'domain': [('id', 'in', self.sign_request_ids.ids)]
        }

    def action_signature_request_wizard(self):
        self.ensure_one()
        action = self.env['ir.actions.actions']._for_xml_id('hr_contract_sign.sign_contract_wizard_action')
        action['context'] = {
            'active_id': self.id,
            'active_model': 'hr.contract',
        }

        return action
