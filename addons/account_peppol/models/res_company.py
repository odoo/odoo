# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    account_peppol_attachment_ids = fields.Many2many(
        comodel_name='ir.attachment',
        string='Peppol Identification Documents',
    )
    account_peppol_proxy_state = fields.Selection(
        selection=[
            ('not_registered', 'Not registered'),
            ('pending', 'Pending'),
            ('manually_approved', 'Approved'),
            ('active', 'Active'),
            ('rejected', 'Rejected'),
        ],
        string='PEPPOL status',
        compute='_compute_account_peppol_proxy_state', required=True, readonly=False, store=True, precompute=True,
    )
    is_account_peppol_participant = fields.Boolean(string='PEPPOL Participant')
    peppol_eas = fields.Selection(related='partner_id.peppol_eas', readonly=False)
    peppol_endpoint = fields.Char(related='partner_id.peppol_endpoint', readonly=False)
    peppol_purchase_journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='PEPPOL Purchase Journal',
        domain=[('type', '=', 'purchase')],
        compute='_compute_peppol_purchase_journal_id', store=True, readonly=False,
    )

    @api.depends('is_account_peppol_participant')
    def _compute_account_peppol_proxy_state(self):
        for company in self:
            if not company.account_peppol_proxy_state:
                company.account_peppol_proxy_state = 'not_registered'

    @api.depends('is_account_peppol_participant')
    def _compute_peppol_purchase_journal_id(self):
        for company in self:
            if company.is_account_peppol_participant and not company.peppol_purchase_journal_id:
                company.peppol_purchase_journal_id = self.env['account.journal'].search(
                    [('company_id', '=', company.id), ('type', '=', 'purchase')],
                    limit=1,
                )
            else:
                company.peppol_purchase_journal_id = False
