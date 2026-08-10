from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    def _l10n_es_manage_dynamic_taxes(self, company, plan, archive_other=True, activate=True):
        template_code = company.chart_template
        if not template_code:
            return

        self.env['account.chart.template'].with_company(company).try_loading(
        template_code, company=company, install_demo=False)

        if plan != 'igic':
            plan = 'aeat'

        plan_csv = {
            'aeat': 'es_common_mainland',
            'igic': 'es_canary_common'
        }
        other_plan = 'igic' if plan == 'aeat' else 'aeat'

        def get_taxes(p):
            parsed = self._parse_csv(plan_csv[p], 'account.tax', module='l10n_es')
            taxes = self.env['account.tax']
            for xml_id in parsed:
                tax = self.ref(xml_id, raise_if_not_found=False)
                if tax:
                    taxes |= tax
            return taxes

        target = get_taxes(plan)
        if target:
            target.write({'active': activate})

        if archive_other:
            other = get_taxes(other_plan)
            if other:
                other.write({'active': False})

    def _l10n_es_manage_dynamic_reports(self, company, plan, archive_other=True, activate=True):
        report_xmlids = {
            'aeat': 'l10n_es.mod_303',
            'igic': 'l10n_es.mod_420'
        }

        if plan != 'igic':
            plan = 'aeat'
        other_plan = 'igic' if plan == 'aeat' else 'aeat'

        def get_report(p):
            return self.env.ref(report_xmlids[p], raise_if_not_found=False)

        target = get_report(plan)
        if target:
            target.active = activate
        if archive_other:
            other = get_report(other_plan)
            if other:
                other.active = False
