# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, Command


class TdsEntryWizard(models.TransientModel):
    _name = 'tds.entry.wizard'
    _description = "Create Tds Entry Wizard"

    date = fields.Date(string="Entry Date", default=fields.Date.today(), copy=False)
    move_id = fields.Many2one('account.move')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id.id, store=True)
    amount_untaxed = fields.Monetary(string="Base Amount", currency_field='currency_id')
    tax_id = fields.Many2one('account.tax', string="TDS Section", readonly=False, domain=[('tax_group_id.name', '=', 'TDS')])
    tds_amount = fields.Monetary(string="TDS Amount", compute='_compute_tds_amount', currency_field='currency_id')
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        string='Journal',
        required=True,
        domain=[('type', '=', 'general')],
        default=lambda self: self.env['account.journal'].search([('type', '=', 'general')], limit=1)
    )
    reference = fields.Char(string="Reference", readonly=True)
    l10n_in_pan = fields.Char(string="PAN Number", readonly=True)
    pan_type = fields.Selection([('company', 'Company'), ('person', 'Individual')], string='PAN Type', readonly=True)

    @api.depends('amount_untaxed', 'tax_id')
    def _compute_tds_amount(self):
        amount_untaxed = self.amount_untaxed
        tds_rate = self.tax_id.amount
        self.tds_amount = amount_untaxed * tds_rate / 100

    @api.model
    def default_get(self, fields_list):
        defaults = super().default_get(fields_list)

        move_id = self.env['account.move'].browse(self.env.context['active_id'])
        defaults['move_id'] = move_id.id
        defaults['amount_untaxed'] = move_id.amount_untaxed
        defaults['reference'] = move_id.name
        defaults['l10n_in_pan'] = move_id.partner_id.l10n_in_pan
        defaults['pan_type'] = move_id.partner_id.company_type
        return defaults

    def create_tds_entry(self):
        commercial_partner_id = self.move_id.commercial_partner_id
        creditors_line = self.move_id.line_ids.filtered(lambda line: line.account_id.internal_group == 'liability')
        move_id = self.env['account.move'].create({
            'l10n_in_move_id': self.move_id.id,
            'move_type': 'entry',
            'ref': self.reference,
            'date': self.date,
            'journal_id': self.journal_id.id,
            'partner_id': commercial_partner_id.id,
            'l10n_in_is_tds': True,

            'line_ids': [
                Command.create({
                'name': self.tax_id.name,
                'account_id': self.tax_id.invoice_repartition_line_ids.account_id.id,
                'partner_id': commercial_partner_id.id,
                'debit': self.tds_amount,
                'tax_tag_ids': [(6, 0, self.tax_id.invoice_repartition_line_ids.tag_ids.ids)],
                'currency_id': self.currency_id.id
                }),
                Command.create({
                'name': f'TDS Deduction on {self.move_id.amount_untaxed}',
                'account_id': commercial_partner_id.property_account_payable_id.id,
                'partner_id': commercial_partner_id.id,
                'credit': self.tds_amount,
                'currency_id': self.currency_id.id,
            })
            ]
        })
        move_id.action_post()
        move_id.js_assign_outstanding_line(creditors_line.id)
