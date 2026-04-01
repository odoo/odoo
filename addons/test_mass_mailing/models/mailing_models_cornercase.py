# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MailingTestPartnerUnstored(models.Model):
    """ Check mailing with unstored fields """
    _name = 'mailing.test.partner.unstored'
    _description = 'Mailing Model without stored partner_id'
    _inherit = ['mail.thread.blacklist']
    _primary_email = 'email_from'

    name = fields.Char()
    email_from = fields.Char()
    partner_id = fields.Many2one(
        'res.partner', 'Customer',
        compute='_compute_partner_id',
        store=False)

    @api.depends('email_from')
    def _compute_partner_id(self):
        partners = self.env['res.partner'].search(
            [('email_normalized', 'in', self.filtered('email_from').mapped('email_normalized'))]
        )
        self.partner_id = False
        for record in self.filtered('email_from'):
            record.partner_id = next(
                (partner.id for partner in partners
                 if partner.email_normalized == record.email_normalized),
                False
            )
