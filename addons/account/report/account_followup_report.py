# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution
#    Copyright (C) 2004-2014 OpenErp S.A. (<http://odoo.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, tools
from datetime import datetime
from hashlib import md5
from openerp.tools.misc import formatLang
from openerp.tools.translate import _


class report_account_followup_report(models.AbstractModel):
    _name = "account.followup.report"
    _description = "Followup Report"

    @api.model
    def get_lines(self, context_id, line_id=None, public=False):
        lines = []
        res = {}
        today = datetime.today().strftime('%Y-%m-%d')
        line_num = 0
        for l in context_id.partner_id.unreconciled_aml_ids:
            if public and l.blocked:
                continue
            currency = l.currency_id or l.company_id.currency_id
            if currency not in res:
                res[currency] = []
            res[currency].append(l)
        for currency, aml_recs in res.items():
            total = 0
            total_issued = 0
            for aml in aml_recs:
                amount = aml.currency_id and aml.amount_residual_currency or aml.amount_residual
                date_due = aml.date_maturity or aml.date
                total += amount
                overdue = today > aml.date_maturity if aml.date_maturity else today > aml.date
                if overdue:
                    total_issued += amount
                    date_due = (date_due, 'color: red;')
                view_type = total >= 0 and 'invoice' or 'payment'
                amount = formatLang(self.env, amount, currency_obj=currency)
                line_num += 1
                lines.append({
                    'id': aml.id,
                    'name': aml.ref,
                    'type': 'unreconciled_aml',
                    'view_type': view_type,
                    'footnotes': self._get_footnotes('unreconciled_aml', aml.id, context_id),
                    'unfoldable': False,
                    'columns': [aml.date, date_due] + (not public and [aml.expected_pay_date and (aml.expected_pay_date, aml.internal_note) or ('', ''), aml.blocked] or []) + [amount],
                })
            total = formatLang(self.env, abs(total), currency_obj=currency)
            line_num += 1
            lines.append({
                'id': line_num,
                'name': total >= 0 and _('Due Total') or '',
                'type': 'line',
                'footnotes': self._get_footnotes('line', 0, context_id),
                'unfoldable': False,
                'level': 0,
                'columns': ['', ''] + (not public and ['', ''] or []) + [total],
            })
            if total_issued > 0:
                total_issued = formatLang(self.env, total_issued, currency_obj=currency)
                line_num += 1
                lines.append({
                    'id': line_num,
                    'name': _('Overdue Total'),
                    'type': 'line',
                    'footnotes': self._get_footnotes('line', 1, context_id),
                    'unfoldable': False,
                    'level': 0,
                    'columns': ['', ''] + (not public and ['', ''] or []) + [total_issued],
                })
        return lines

    @api.model
    def _get_footnotes(self, type, target_id, context_id):
        footnotes = context_id.footnotes.filtered(lambda s: s.type == type and s.target_id == target_id)
        result = {}
        for footnote in footnotes:
            result.update({footnote.column: footnote.number})
        return result

    @api.model
    def get_title(self):
        return _('Followup Report')

    @api.model
    def get_name(self):
        return 'followup_report'

    @api.model
    def get_report_type(self):
        return 'custom'

    @api.model
    def get_template(self):
        return 'account.report_followup'


class account_report_context_followup_all(models.TransientModel):
    _name = "account.report.context.followup.all"
    _description = "A progress bar for followup reports"

    @api.depends('valuenow', 'valuemax')
    def _compute_percentage(self):
        for progressbar in self:
            progressbar.percentage = 100 * progressbar.valuenow / progressbar.valuemax

    valuenow = fields.Integer('current amount of invoices done', default=0)
    valuemax = fields.Integer('total amount of invoices to do')
    percentage = fields.Integer(compute='_compute_percentage')
    started = fields.Datetime('Starting time', default=lambda self: fields.datetime.now())
    partner_filter = fields.Selection([('all', 'All partners with overdue invoices'), ('action', 'All partners in need of action')], string='Partner Filter', default='action')
    skipped_partners_ids = fields.Many2many('res.partner', 'account_fup_report_skipped_partners', string='Skipped partners')

    def skip_partner(self, partner):
        self.write({'skipped_partners_ids': [(4, partner.id)]})
        self.write({'valuenow': self.valuenow + 1})

    def get_total_time(self):
        delta = fields.datetime.now() - datetime.strptime(self.started, tools.DEFAULT_SERVER_DATETIME_FORMAT)
        return delta.seconds

    def get_time_per_report(self):
        return round(self.get_total_time() / self.valuemax, 2)

    def get_alerts(self):
        alerts = []
        if self.valuemax > 4 and self.valuemax / 2 == self.valuenow:
            alerts.append({
                'title': _('Halfway through!'),
                'message': _('The first half took you %ss.') % str(self.get_total_time()),
            })
        if self.valuemax > 50 and round(self.valuemax * 0.9) == self.valuenow:
            alerts.append({
                'title': _('10% remaining!'),
                'message': _("Hang in there, you're nearly done."),
            })
        return alerts


class account_report_context_followup(models.TransientModel):
    _name = "account.report.context.followup"
    _description = "A particular context for the followup report"
    _inherit = "account.report.context.common"

    footnotes = fields.Many2many('account.report.footnote', 'account_context_footnote_followup', string='Footnotes')
    partner_id = fields.Many2one('res.partner', string='Partner')
    summary = fields.Char(default=lambda s: s.env.user.company_id.overdue_msg and s.env.user.company_id.overdue_msg.replace('\n', '<br />') or s.env['res.company'].default_get(['overdue_msg'])['overdue_msg'])

    @api.multi
    def change_next_action(self, date, note):
        self.partner_id.write({'payment_next_action': note, 'payment_next_action_date': date})
        msg = _('Next action date: ') + date + '.\n' + note
        self.partner_id.message_post(body=msg, subtype='account.followup_logged_action')

    @api.multi
    def add_footnote(self, type, target_id, column, number, text):
        footnote = self.env['account.report.footnote'].create(
            {'type': type, 'target_id': target_id, 'column': column, 'number': number, 'text': text}
        )
        self.write({'footnotes': [(4, footnote.id)]})

    @api.model
    def get_partners(self):
        return self.env['res.partner'].search([])

    @api.multi
    def edit_footnote(self, number, text):
        footnote = self.footnotes.filtered(lambda s: s.number == number)
        footnote.write({'text': text})

    @api.multi
    def remove_footnote(self, number):
        footnotes = self.footnotes.filtered(lambda s: s.number == number)
        self.write({'footnotes': [(3, footnotes.id)]})

    def get_report_obj(self):
        return self.env['account.followup.report']

    @api.multi
    def remove_line(self, line_id):
        return

    @api.multi
    def add_line(self, line_id):
        return

    def get_columns_names(self):
        if self.env.context.get('public'):
            return [_('Date'), _('Due Date'), _('Total Due')]
        return [_('Date'), _('Due Date'), _('Expected Date'), _('Litigated'), _('Total Due')]

    def get_pdf(self, log=False):
        bodies = []
        for context in self:
            context = context.with_context(lang=context.partner_id.lang)
            report_obj = context.get_report_obj()
            lines = report_obj.get_lines(context, public=True)
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            rcontext = {
                'context': context,
                'report': report_obj,
                'lines': lines,
                'mode': 'print',
                'base_url': base_url,
                'css': '',
                'o': self.env.user,
                'today': datetime.today().strftime('%Y-%m-%d'),
            }
            html = self.pool['ir.ui.view'].render(self._cr, self._uid, report_obj.get_template() + '_letter', rcontext, context=context.env.context)
            bodies.append((0, html))
            if log:
                msg = fields.Date.context_today(self) + _(': Sent a followup letter')
                context.partner_id.message_post(body=msg, subtype='account.followup_logged_action')

        return self.env['report']._run_wkhtmltopdf([], [], bodies, False, self.env.user.company_id.paperformat_id)

    @api.multi
    def send_email(self):
        pdf = self.get_pdf().encode('base64')
        name = self.partner_id.name + '_followup.pdf'
        attachment = self.env['ir.attachment'].create({'name': name, 'datas_fname': name, 'datas': pdf, 'type': 'binary'})
        email = self.env['res.partner'].browse(self.partner_id.address_get(['invoice'])['invoice']).email
        if email and email.strip():
            email_template = self.env['mail.template'].create({
                'name': _('Followup ') + self.partner_id.name,
                'email_from': self.env.user.email or '',
                'model_id': 1,
                'subject': _('%s Payment Reminder') % self.env.user.company_id.name,
                'email_to': email,
                'lang': self.partner_id.lang,
                'auto_delete': True,
                'body_html': self.summary,
                'attachment_ids': [(6, 0, [attachment.id])],
            })
            email_template.send_mail(self.id)
            msg = fields.Date.context_today(self) + _(': Sent a followup email')
            self.partner_id.message_post(body=msg, subtype='account.followup_logged_action')
            return True
        return False

    @api.multi
    def get_public_link(self):
        db_uuid = self.env['ir.config_parameter'].get_param('database.uuid')
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        check = md5(str(db_uuid) + self.partner_id.name).hexdigest()
        return base_url + '/account/public_followup_report/' + str(self.partner_id.id) + '/' + check

    def get_history(self):
        return self.env['mail.message'].search([('subtype_id', '=', self.env['ir.model.data'].xmlid_to_res_id('account.followup_logged_action')), ('id', 'in', self.partner_id.message_ids.ids)], limit=5)
