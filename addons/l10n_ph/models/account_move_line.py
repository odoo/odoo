"""Payment voucher helpers for account move lines."""

from odoo import models
from odoo.tools.float_utils import float_round
from odoo.tools.misc import formatLang, get_lang


class AccountMoveLine(models.Model):
    """Extend journal items with report-friendly analytic distribution formatting."""

    _inherit = "account.move.line"

    def _get_analytic_distribution_plan_summaries(self):
        self.ensure_one()

        if not self.analytic_distribution:
            return []

        analytic_distribution = self.analytic_distribution
        analytic_keys = [key for key in analytic_distribution if key != '__update__']
        analytic_account_ids = sorted({
            int(account_id)
            for account_ids in analytic_keys
            for account_id in account_ids.split(',')
            if account_id.isdigit()
        })

        analytic_accounts = self.env['account.analytic.account'].with_context(active_test=False)
        accounts_by_id = {
            account.id: account
            for account in analytic_accounts.browse(analytic_account_ids).exists()
        }
        plans_summary = {}

        for account_ids, distribution in analytic_distribution.items():
            if account_ids == '__update__':
                continue
            valid_account_ids = [
                int(account_id)
                for account_id in account_ids.split(',')
                if account_id.isdigit()
            ]
            for account_id in valid_account_ids:
                account = accounts_by_id.get(account_id)
                if not account:
                    continue

                plan = account.root_plan_id
                plan_summary = plans_summary.setdefault(plan.id, {
                    'plan': plan,
                    'accounts': {},
                })
                account_summary = plan_summary['accounts'].setdefault(account.id, {
                    'account': account,
                    'total': 0.0,
                })
                account_summary['total'] += float(distribution or 0.0)

        return [plans_summary[plan_id] for plan_id in sorted(plans_summary)]

    def _format_analytic_distribution_percentage(self, value, precision):
        decimal_point = get_lang(self.env).decimal_point
        formatted = formatLang(
            self.env,
            float_round(value, precision_digits=precision),
            digits=precision,
            grouping=False,
        )
        if precision:
            formatted = formatted.rstrip('0').rstrip(decimal_point)
        return f"{formatted}%"

    def _is_analytic_distribution_complete(self, total, precision):
        return float_round(total, precision_digits=precision) == 100

    def _get_analytic_distribution_plain_text(self):
        self.ensure_one()
        plan_summaries = self._get_analytic_distribution_plan_summaries()
        if not plan_summaries:
            return ""

        precision = self.analytic_precision or self.env[
            'decimal.precision'
        ].precision_get('Percentage Analytic')
        plan_texts = []
        for plan_summary in plan_summaries:
            account_summaries = [
                plan_summary['accounts'][account_id]
                for account_id in sorted(plan_summary['accounts'])
            ]
            account_texts = []
            for account_summary in account_summaries:
                if self._is_analytic_distribution_complete(account_summary['total'], precision):
                    account_texts.append(account_summary['account'].display_name)
                else:
                    percentage_text = self._format_analytic_distribution_percentage(
                        account_summary['total'],
                        precision,
                    )
                    account_texts.append(
                        f"{percentage_text} "
                        f"{account_summary['account'].display_name}"
                    )
            plan_texts.append(", ".join(account_texts))
        return '\n'.join(plan_texts)
