from openerp import http
from openerp.http import request


class FinancialReportController(http.Controller):

    def get_report_obj_from_name(self, name, id=None):
        uid = request.session.uid
        if name == 'financial_report':
            return request.env['account.financial.report'].sudo(uid)
        if name == 'generic_tax_report':
            return request.env['account.generic.tax.report'].sudo(uid)

    @http.route('/account/<string:report_name>/<string:report_id>', type='http', auth='none')
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
        if not context_id:
            create_vals = {}
            if report_name == 'financial_report':
                create_vals['report_id'] = report_id
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
        if kw:
            update = {}
            for field in context_id._fields:
                if kw.get(field):
                    update[field] = kw[field]
                elif field in ['cash_basis', 'comparison', 'all_entries']:
                    update[field] = False
            context_id.write(update)
        lines = report_obj.get_lines(context_id)
        rcontext = {
            'context': context_id,
            'o': report_obj,
            'lines': lines,
            'mode': 'display',
        }
        return request.render("account.report_financial", rcontext)
