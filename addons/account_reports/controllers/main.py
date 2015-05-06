from openerp import http, fields
from openerp.http import request
from hashlib import md5
from openerp.tools.safe_eval import safe_eval
import time
from datetime import datetime


class FinancialReportController(http.Controller):

    def get_report_obj_from_name(self, name, id=None):
        uid = request.session.uid
        if name == 'financial_report':
            return request.env['account.financial.report'].sudo(uid)
        if name == 'generic_tax_report':
            return request.env['account.generic.tax.report'].sudo(uid)
        if name == 'bank_reconciliation':
            return request.env['account.bank.reconciliation.report'].sudo(uid)
        if name == 'general_ledger':
            return request.env['account.general.ledger'].sudo(uid)
        if name == 'l10n_be_partner_vat_listing':
            return request.env['l10n.be.report.partner.vat.listing'].sudo(uid)

    @http.route('/account/<string:report_name>/<string:report_id>', type='http', auth='user')
    def report(self, report_name, report_id=None, **kw):
        uid = request.session.uid
        domain = [('create_uid', '=', uid)]
        report_obj = self.get_report_obj_from_name(report_name)
        if report_name == 'financial_report':
            report_id = int(report_id)
            domain.append(('report_id', '=', report_id))
            report_obj = report_obj.browse(report_id)
        context_obj = request.env['account.report.context.common'].get_context_by_report_name(report_name)
        context_id = context_obj.sudo(uid).search(domain, limit=1)
        if context_id and (('force_account' in kw and report_name == 'general_ledger') or 'force_fy' in kw):
            context_id.unlink()
            context_id = context_id.exists()
        if not context_id:
            create_vals = {}
            if report_name == 'financial_report':
                create_vals['report_id'] = report_id
            if 'force_account' in kw and report_name == 'general_ledger':
                create_vals['unfolded_accounts'] = [(4, kw['force_account'])]
            if 'force_fy' in kw:
                create_vals['force_fy'] = True
            context_id = context_obj.sudo(uid).create(create_vals)
        if 'xls' in kw:
            response = request.make_response(None,
                headers=[('Content-Type', 'application/vnd.ms-excel'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.xls;')])
            context_id.get_xls(response)
            return response
        if 'pdf' in kw:
            return request.make_response(context_id.get_pdf(),
                headers=[('Content-Type', 'application/pdf'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.pdf;')])
        if 'xml' in kw:
            content = context_id.get_xml()
            return request.make_response(content,
                headers=[('Content-Type', 'application/vnd.sun.xml.writer'),
                         ('Content-Disposition', 'attachment; filename=' + report_obj.get_name() + '.xml;'),
                         ('Content-Length', len(content))])
        if kw:
            update = {}
            for field in kw:
                if context_id._fields.get(field) and kw[field] != 'undefined':
                    if kw[field] == 'false':
                        kw[field] = False
                    update[field] = kw[field]
            context_id.write(update)
        lines = report_obj.get_lines(context_id)
        rcontext = {
            'res_company': request.env['res.users'].browse(uid).company_id,
            'context': context_id,
            'report': report_obj,
            'lines': lines,
            'mode': 'display',
        }
        return request.render(report_obj.get_template(), rcontext)

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
        partners = request.env['res.partner'].get_partners_in_need_of_action() - context_all_id.skipped_partners_ids
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
                    context_all_id.write({'valuenow': min(context_all_id.valuemax, context_all_id.valuenow + 2)})
                    partners = partners - partners_done
                else:
                    context_all_id.write({'valuenow': context_all_id.valuenow + 1})
        if context_all_id.valuemax != context_all_id.valuenow + len(partners):
            context_all_id.write({'valuemax': context_all_id.valuenow + len(partners)})
        if context_all_id.partner_filter == 'all':
            partners = request.env['res.partner'].get_partners_in_need_of_action(overdue_only=True)
        for partner in partners[((page - 1) * 15):(page * 15)]:
            context_id = context_obj.sudo(uid).search([('partner_id', '=', partner.id)], limit=1)
            if not context_id:
                context_id = context_obj.with_context(lang=partner.lang).create({'partner_id': partner.id})
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
            'emails_not_sent': emails_not_sent,
            'last_page': (len(partners) - 1) / 15 == page - 1,
            'context_all': context_all_id,
            'all_partners_done': kw.get('partner_done') == 'all',
            'just_arrived': 'partner_done' not in kw and 'partner_skipped' not in kw,
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
        partner = request.env['res.partner'].browse(partner)
        if 'partner_done' in kw:
            partners = request.env['res.partner'].get_partners_in_need_of_action()
            if not partners:
                return self.followup_all(partner_done=kw['partner_done'])
            partner = partners[0]
        context_id = context_obj.sudo(uid).search([('partner_id', '=', partner.id)], limit=1)
        if not context_id:
            context_id = context_obj.with_context(lang=partner.lang).create({'partner_id': partner.id})
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
            'today': datetime.today().strftime('%Y-%m-%d'),
            'res_company': request.env['res.users'].browse(uid).company_id,
        }
        return request.render('account_reports.report_followup', rcontext)


    @http.route('/account/public_followup_report/<int:partner>/<string:password>', type='http', auth='none')
    def followup_public(self, partner, password, **kw):
        partner = request.env['res.partner'].sudo().browse(partner)
        db_uuid = request.env['ir.config_parameter'].get_param('database.uuid')
        check = md5(str(db_uuid) + partner.name).hexdigest()
        if check != password:
            return request.not_found()
        context_obj = request.env['account.report.context.followup']
        report_obj = request.env['account.followup.report']
        context_id = context_obj.sudo().search([('partner_id', '=', int(partner))], limit=1)
        if not context_id:
            context_id = context_obj.sudo().with_context(lang=partner.lang).create({'partner_id': int(partner)})
        lines = report_obj.sudo().with_context(lang=partner.lang).get_lines(context_id, public=True)
        rcontext = {
            'context': context_id.with_context(lang=partner.lang, public=True),
            'report': report_obj.with_context(lang=partner.lang),
            'lines': lines,
            'mode': 'display',
            'res_company': request.env['res.users'].browse(request.session.uid).company_id,
        }
        return request.render('account_reports.report_followup_public', rcontext)
