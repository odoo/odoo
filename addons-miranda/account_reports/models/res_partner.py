# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    def change_expected_date(self, options=False):
        if not options or 'expected_pay_date' not in options or 'move_line_id' not in options:
            return True
        for record in self:
            aml = self.env['account.move.line'].search([('id', '=', int(options['move_line_id']))], limit=1)
            old_date = aml.expected_pay_date
            aml.write({'expected_pay_date': options['expected_pay_date']})
            partner_msg = _('Expected pay date has been changed from %s to %s for invoice %s') % (old_date or _('any'), aml.expected_pay_date, aml.move_id.name)
            record.message_post(body=partner_msg)
            move_msg = _('Expected pay date has been changed from %s to %s') % (old_date or _('any'), aml.expected_pay_date)
            aml.move_id.message_post(body=move_msg)
        return True

    def open_partner_ledger(self):
        return {
            'type': 'ir.actions.client',
            'name': _('Partner Ledger'),
            'tag': 'account_report',
            'options': {'partner_ids': [self.id]},
            'ignore_session': 'both',
            'context': "{'model':'account.partner.ledger'}"
        }
