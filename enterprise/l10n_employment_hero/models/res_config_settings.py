# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    employment_hero_api_key = fields.Char(related='company_id.employment_hero_api_key', readonly=False)
    employment_hero_base_url = fields.Char(related='company_id.employment_hero_base_url', readonly=False)
    employment_hero_enable = fields.Boolean(related='company_id.employment_hero_enable', readonly=False)
    employment_hero_identifier = fields.Char(related='company_id.employment_hero_identifier', readonly=False)
    employment_hero_lock_date = fields.Date(related='company_id.employment_hero_lock_date', readonly=False)
    employment_hero_journal_id = fields.Many2one(related='company_id.employment_hero_journal_id', readonly=False)

    @api.onchange('employment_hero_enable')
    def _onchange_employment_hero_enable(self):
        if not self.employment_hero_journal_id:
            self.employment_hero_journal_id = self.env['account.journal'].search([
                *self.env['account.journal']._check_company_domain(self.company_id),
                ('type', '=', 'general'),
            ], limit=1)

    def action_eh_payroll_fetch_payrun(self):
        account_moves = self.company_id._eh_payroll_fetch_payrun()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Payruns fetched',
                'message': _("%(payrun_amount)s payruns were fetched and added to your accounting",
                             payrun_amount=len(account_moves)),
                'sticky': True,
            }
        }
