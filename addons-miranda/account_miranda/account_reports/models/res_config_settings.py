# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import format_date
from odoo.tools import date_utils


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    totals_below_sections = fields.Boolean(related='company_id.totals_below_sections', string='Add totals below sections', readonly=False,
                                           help='When ticked, totals and subtotals appear below the sections of the report.')
    account_tax_periodicity = fields.Selection(related='company_id.account_tax_periodicity', string='Periodicity', readonly=False, required=True)
    account_tax_periodicity_reminder_day = fields.Integer(related='company_id.account_tax_periodicity_reminder_day', string='Reminder', readonly=False, required=True)
    account_tax_periodicity_journal_id = fields.Many2one(related='company_id.account_tax_periodicity_journal_id', string='Journal', readonly=False)

    def set_values(self):
        super(ResConfigSettings, self).set_values()
        company = self.company_id or self.env.company
        if not self.has_chart_of_accounts or (company.account_tax_original_periodicity_reminder_day and company.account_tax_original_periodicity_reminder_day == self.account_tax_periodicity_reminder_day):
            return True
        self._update_account_tax_periodicity_reminder_day()

    @api.model
    def _update_account_tax_periodicity_reminder_day(self):
        company = self.company_id or self.env.company
        move_id = self._create_edit_tax_reminder()
        move_to_delete = self.env['account.move'].search([
            ('id', '!=', move_id.id),
            ('state', '=', 'draft'),
            ('activity_ids.activity_type_id', '=', company.account_tax_next_activity_type.id),
            ('company_id', '=', company.id)
        ])
        if len(move_to_delete):
            journal_to_reset = [a.journal_id.id for a in move_to_delete]
            move_to_delete.unlink()
            self.env['account.journal'].browse(journal_to_reset).write({'show_on_dashboard': False})

        # Finally, add the journal visible in the dashboard
        company.account_tax_periodicity_journal_id.show_on_dashboard = True

    def _create_edit_tax_reminder(self, values=None):
        # Create/Edit activity type if needed
        if self._context.get('no_create_move', False):
            return self.env['account.move']
        if not values:
            values = {}
        company = values.get('company_id', False) or self.company_id or self.env.company
        move_res_model_id = self.env['ir.model'].search([('model', '=', 'account.move')], limit=1).id
        activity_type = company.account_tax_next_activity_type or False
        vals = {
            'category': 'tax_report',
            'delay_count': values.get('account_tax_periodicity', company.account_tax_periodicity) == 'monthly' and 1 or 3,
            'delay_unit': 'months',
            'delay_from': 'previous_activity',
            'res_model_id': move_res_model_id,
            'force_next': False,
            'summary': _('Periodic Tax Return')
        }
        if not activity_type:
            vals['name'] = _('Tax Report for company %s') % (company.name,)
            activity_type = self.env['mail.activity.type'].create(vals)
            company.account_tax_next_activity_type = activity_type
        else:
            activity_type.write(vals)

        # search for an existing reminder for given journal and change it's date
        account_tax_periodicity_journal_id = values.get('account_tax_periodicity_journal_id', company.account_tax_periodicity_journal_id)
        date = values.get('account_tax_periodicity_next_deadline', False)
        if not date:
            date = date_utils.end_of(fields.Date.today(), "quarter") + relativedelta(days=company.account_tax_periodicity_reminder_day)
        end_date_last_month = date_utils.end_of(date + relativedelta(months=-1), 'month')
        move_id = self.env['account.move'].search([
            ('state', '=', 'draft'),
            ('is_tax_closing', '=', True),
            ('journal_id', '=', account_tax_periodicity_journal_id.id),
            ('activity_ids.activity_type_id', '=', activity_type.id),
            ('date', '<=', end_date_last_month),
            ('date', '>=', date_utils.start_of(end_date_last_month + relativedelta(months=-vals['delay_count']), 'month'))
        ], limit=1)
        # Create empty move
        if activity_type.delay_count == 1:
            formatted_date = format_date(self.env, end_date_last_month, date_format='LLLL')
        else:
            formatted_date = format_date(self.env, end_date_last_month, date_format='qqq')
        if len(move_id):
            for act in move_id.activity_ids:
                if act.activity_type_id == activity_type:
                    act.write({'date_deadline': date})
            move_id.date = end_date_last_month
            move_id.ref = _('Tax Return for %s') % (formatted_date,)
        else:
            move_id = self.env['account.move'].create({
                'journal_id': account_tax_periodicity_journal_id.id,
                'date': end_date_last_month,
                'is_tax_closing': True,
                'ref': _('Tax Return for %s') % (formatted_date,)
            })
            advisor_user = self.env['res.users'].search(
                [('company_ids', 'in', (company.id,)), ('groups_id', 'in', self.env.ref('account.group_account_manager').ids)],
                limit=1, order="id ASC")
            activity_vals = {
                'res_id': move_id.id,
                'res_model_id': move_res_model_id,
                'activity_type_id': activity_type.id,
                'summary': _('TAX Report'),
                'date_deadline': date,
                'automated': True,
                'user_id':  advisor_user.id or self.env.user.id
            }
            self.env['mail.activity'].with_context(mail_activity_quick_update=True).create(activity_vals)
        return move_id
