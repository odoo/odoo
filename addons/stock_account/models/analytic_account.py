#  -*- coding: utf-8 -*-
#  Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models
from odoo.tools import float_compare, float_is_zero


class AccountAnalyticPlan(models.Model):
    _inherit = 'account.analytic.plan'

    def _calculate_distribution_amount(self, amount, percentage, distribution_on_each_plan):
        existing_amount = distribution_on_each_plan.get(self, 0)
        distribution_plan = existing_amount + percentage
        decimal_precision = self.env['decimal.precision'].precision_get('Percentage Analytic')
        if float_compare(distribution_plan, 100, precision_digits=decimal_precision) == 0:
            distributed_amount = amount * (100 - existing_amount) / 100.0
        else:
            distributed_amount = amount * percentage / 100.0
        distribution_on_each_plan[self] = distribution_plan
        return distributed_amount

class AccountAnalyticAccount(models.Model):
    _inherit = 'account.analytic.account'

    def _perform_analytic_distribution(self, distribution, amount, unit_amount, lines, obj, additive=False):
        """
        Redistributes the analytic lines to match the given distribution:
            - For account_ids where lines already exist, the amount and unit_amount of these lines get updated,
              lines where the updated amount becomes zero get unlinked.
            - For account_ids where lines don't exist yet, the line values to create them are returned,
              lines where the amount becomes zero are not included.

        :param distribution:    the desired distribution to match the analytic lines to
        :param amount:          the total amount to distribute over the analytic lines
        :param unit_amount:     the total unit amount (will not be distributed)
        :param lines:           the (current) analytic account lines that need to be matched to the new distribution
        :param obj:             the object on which _prepare_analytic_line_values(account_id, amount, unit_amount) will be
                                called to get the template for the values of new analytic line objects
        :param additive:        if True, the unit_amount and (distributed) amount get added to the existing lines

        :returns: a list of dicts containing the values for new analytic lines that need to be created
        :rtype:   dict
        """
        distribution_on_each_plan = {}
        processed_distributions = []
        for existing_aal in lines:
            if distribution and existing_aal.account_id.id in [int(i) for i in distribution]:
                # Update the existing AAL for this account
                percentage = distribution[str(existing_aal.account_id.id)]
                new_amount = existing_aal.account_id.root_plan_id._calculate_distribution_amount(amount, percentage, distribution_on_each_plan)
                new_unit_amount = amount
                if additive:
                    new_amount += existing_aal.amount
                    new_unit_amount += existing_aal.unit_amount
                currency = existing_aal.account_id.currency_id or obj.company_id.currency_id
                if float_is_zero(new_amount, precision_rounding=currency.rounding):
                    existing_aal.unlink()
                else:
                    existing_aal.amount = new_amount
                    existing_aal.unit_amount = new_unit_amount
                processed_distributions.append(existing_aal.account_id.id)
            else:
                # Delete the existing AAL if it is no longer present in the new distribution
                existing_aal.unlink()
        lines_to_link = []
        if not distribution:
            return []
        for account_id, percentage in distribution.items():
            # Only create a new AAL if an existing one was not already modified before
            account_id = int(account_id)
            if account_id not in processed_distributions:
                account = self.browse(account_id)
                new_amount = account.root_plan_id._calculate_distribution_amount(amount, percentage, distribution_on_each_plan)
                currency = account.currency_id or obj.company_id.currency_id
                if not float_is_zero(new_amount, precision_rounding=currency.rounding):
                    lines_to_link.append(obj._prepare_analytic_line_values(account.id, new_amount, unit_amount))
        return lines_to_link
