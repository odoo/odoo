# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _


class ResPartner(models.Model):
    _inherit = 'res.partner'

    signature_count = fields.Integer(compute='_compute_signature_count', string="# Signatures")

    def _compute_signature_count(self):
        signature_data = self.env['sign.request.item'].sudo()._read_group([('partner_id', 'in', self.ids), ('state', 'in', ['sent', 'completed'])], ['partner_id'], ['__count'])
        signature_data_mapped = {partner.id: count for partner, count in signature_data}
        for partner in self:
            partner.signature_count = signature_data_mapped.get(partner.id, 0)

    def open_signatures(self):
        self.ensure_one()
        request_ids = self.env['sign.request.item'].search([('partner_id', '=', self.id)]).mapped('sign_request_id')
        return {
            'type': 'ir.actions.act_window',
            'name': _('Signature(s)'),
            'view_mode': 'kanban,list,form',
            'res_model': 'sign.request',
            'domain': [('id', 'in', request_ids.ids)],
            'context': {
                'search_default_reference': self.name,
                'search_default_signed': 1,
                'search_default_in_progress': 1,
            },
        }

    def write(self, vals):
        partners_email_changed = False
        if vals.get('email'):
            # Email is changed by removing it or changing characters (not casing).
            partners_email_changed = self.filtered(
                lambda r: not r.email or r.email.lower() != vals['email'].lower()
            )
        res = super().write(vals)
        if partners_email_changed:
            request_items = self.env['sign.request.item'].sudo().search([
                ('partner_id', 'in', partners_email_changed.ids),
                ('state', '=', 'sent'),
                ('is_mail_sent', '=', True)])
            for request_item in request_items:
                request_item.sign_request_id.message_post(
                    body=_('The mail address of %(partner)s has been updated. The request will be automatically resent.',
                           partner=request_item.partner_id.name))
                self.env['sign.log'].sudo().create({'sign_request_item_id': request_item.id, 'action': 'update_mail'})
                request_item.access_token = self.env['sign.request.item']._default_access_token()
            request_items.send_signature_accesses()
        return res
