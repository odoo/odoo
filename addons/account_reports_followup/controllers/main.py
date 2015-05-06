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

from openerp import http, addons
from openerp.http import request
from openerp.tools.safe_eval import safe_eval
import time
from datetime import datetime


class FollowupReportController(addons.account_reports.controllers.main.FinancialReportController):

    @http.route(['/account/followup_report/all/', '/account/followup_report/all/page/<int:page>'], type='http', auth='user')
    def followup_all(self, page=1, **kw):
        uid = request.session.uid
        context_obj = request.env['account.report.context.followup']
        report_obj = request.env['account.followup.report']
        context_all_obj = request.env['account.report.context.followup.all']
        reports = []
        emails_not_sent = context_obj.browse()
        context_all_id = context_all_obj.sudo(uid).search([('create_uid', '=', uid)], limit=1)
        if 'letter_context_list' in kw and 'pdf' in kw:
            letter_context_list = safe_eval('[' + kw['letter_context_list'] + ']')
            letter_contexts = request.env['account.report.context.followup'].browse(letter_context_list)
            return request.make_response(letter_contexts.with_context(public=True).get_pdf(log=True),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=followups.pdf;')])
        if 'partner_skipped' in kw:
            context_all_id.skip_partner(request.env['res.partner'].browse(int(kw['partner_skipped'])))
        partners_data = request.env['res.partner'].get_partners_in_need_of_action_and_update()
        partners = request.env['res.partner'].browse(partners_data.keys()) - context_all_id.skipped_partners_ids
        action_contexts = []
        if not context_all_id:
            context_all_id = context_all_obj.sudo(uid).create({'valuemax': len(partners)})
        if 'partner_filter' in kw:
            context_all_id.write({'partner_filter': kw['partner_filter']})
        if 'partner_done' in kw and 'partner_filter' not in kw:
            try:
                context_all_id.write({'skipped_partners_ids': [(4, int(kw['partner_done']))]})
            except ValueError:
                pass
            if context_all_id.partner_filter == 'action':
                if kw['partner_done'] == 'all':
                    if 'email_context_list' in kw:
                        email_context_list = safe_eval('[' + kw['email_context_list'] + ']')
                        email_contexts = request.env['account.report.context.followup'].browse(email_context_list)
                        for email_context in email_contexts:
                            if not email_context.send_email():
                                emails_not_sent = emails_not_sent | email_context
                    partners_done = partners[((page - 1) * 15):(page * 15)] - emails_not_sent.partner_id
                    partners_done.update_next_action()
                    context_all_id.write({'valuenow': min(context_all_id.valuemax, context_all_id.valuenow + 15)})
                    partners = partners - partners_done
                    if 'action_context_list' in kw:
                        action_context_list = safe_eval('[' + kw['action_context_list'] + ']')
                        action_contexts = request.env['account.report.context.followup'].browse(action_context_list)
                else:
                    context_all_id.write({'valuenow': context_all_id.valuenow + 1})
        if context_all_id.valuemax != context_all_id.valuenow + len(partners):
            context_all_id.write({'valuemax': context_all_id.valuenow + len(partners)})
        if context_all_id.partner_filter == 'all':
            partners = request.env['res.partner'].get_partners_in_need_of_action(overdue_only=True)
        for partner in partners[((page - 1) * 15):(page * 15)]:
            context_id = context_obj.sudo(uid).search([('partner_id', '=', partner.id)], limit=1)
            if not context_id:
                vals = {'partner_id': partner.id}
                if partner.id in partners_data:
                    vals.update({'level': partners_data[partner.id][0]})
                context_id = context_obj.with_context(lang=partner.lang).create(vals)
            lines = report_obj.with_context(lang=partner.lang).get_lines(context_id)
            reports.append({
                'context': context_id.with_context(lang=partner.lang),
                'lines': lines,
            })
        rcontext = {
            'reports': reports,
            'report': report_obj,
            'mode': 'display',
            'page': page,
            'last_page': (len(partners) - 1) / 3 == page - 1,
            'context_all': context_all_id,
            'all_partners_done': kw.get('partner_done') == 'all',
            'just_arrived': 'partner_done' not in kw and 'partner_skipped' not in kw,
            'action_contexts': action_contexts,
            'time': time,
            'today': datetime.today().strftime('%Y-%m-%d'),
            'res_company': request.env['res.users'].browse(uid).company_id,
        }
        return request.render('account_reports.report_followup_all', rcontext)

    @http.route('/account/followup_report/<int:partner>/', type='http', auth='user')
    def followup(self, partner, **kw):
        uid = request.session.uid
        context_obj = request.env['account.report.context.followup']
        report_obj = request.env['account.followup.report']
        partners_data = request.env['res.partner'].get_partners_in_need_of_action_and_update()
        partner = request.env['res.partner'].browse(partner)
        partners = partners_data.keys()
        if 'partner_done' in kw:
            if not partners:
                return self.followup_all(partner_done=kw['partner_done'])
            partner = request.env['res.partner'].browse(partners[0])
        context_id = context_obj.sudo(uid).search([('partner_id', '=', partner.id)], limit=1)
        if not context_id:
            vals = {'partner_id': partner.id}
            if partner.id in partners:
                vals.update({'level': partners_data[partner.id][0]})
            context_id = context_obj.with_context(lang=partner.lang).create(vals)
        if 'pdf' in kw:
            return request.make_response(context_id.with_context(lang=partner.lang, public=True).get_pdf(log=True),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=' + partner.name + '.pdf;')])
        lines = report_obj.with_context(lang=partner.lang).get_lines(context_id)
        rcontext = {
            'context': context_id.with_context(lang=partner.lang),
            'report': report_obj.with_context(lang=partner.lang),
            'lines': lines,
            'mode': 'display',
            'time': time,
            'res_company': request.env['res.users'].browse(uid).company_id,
        }
        return request.render('account_reports.report_followup', rcontext)
