# Part of Odoo. See LICENSE file for full copyright and licensing details.
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class L10nChCompensationFund(models.Model):
    _inherit = 'l10n.ch.compensation.fund'

    paid_by_fcf = fields.Boolean('Child allowances paid by FCF')
    caf_scale_ids = fields.One2many(
        'l10n.ch.caf.scale',
        'fund_id',
        string="Allowance Scales"
    )

    def _get_family_allowances(self, children, target_date):
        self.ensure_one()
        input_values = []

        # Load Input Types
        child_allowance_input = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3000')
        education_allowance_input = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_input_WT_3010')
        child_allowance_input_fcf = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3004_input_fcf')
        education_allowance_input_fcf = self.env.ref('l10n_ch_hr_payroll_elm_transmission.l10n_ch_elm_3014_input_fcf')

        if not self.caf_scale_ids:
            return []

        eligible_children_data = []

        for child in children:
            if not child.allowance_eligible or not child.birthdate:
                continue

            if child.allowance_start_date and target_date < child.allowance_start_date:
                continue

            age_rel = relativedelta(target_date, child.birthdate)
            age_years = age_rel.years

            eligible_children_data.append({
                'obj': child,
                'age': age_years,
                'birthdate': child.birthdate,
                'is_extended_child': child.l10n_ch_child_status == 'dependent'
            })

        eligible_children_data.sort(key=lambda x: x['birthdate'])

        for index, child_data in enumerate(eligible_children_data):
            child_rank = index + 1
            child_age = child_data['age']
            child_obj = child_data['obj']
            child_is_extended_dep = child_data['is_extended_child']

            valid_rules = self.caf_scale_ids.filtered(
                lambda r: r.min_age <= child_age <= r.max_age
            )
            if not valid_rules and child_is_extended_dep:
                filter_type_condition = 'child' if target_date <= child_obj.child_allowance_end_date else 'education'
                rules_grouped_by_childrank = valid_rules.filtered(lambda r: r.allowance_type == filter_type_condition).grouped('min_child_rank')
                for rank, rank_rules in rules_grouped_by_childrank.items():
                    valid_rules += max(rank_rules, key=lambda r: r.min_age)

            valid_rules = valid_rules.sorted(key=lambda r: r.min_child_rank, reverse=True)

            matched_rule = None

            for rule in valid_rules:
                if child_rank < rule.min_child_rank:
                    continue

                is_date_valid = False

                if rule.allowance_type == 'child':
                    if child_obj.child_allowance_end_date and target_date <= child_obj.child_allowance_end_date:
                        is_date_valid = True
                elif rule.allowance_type == 'education':
                    if child_obj.education_allowance_end_date and target_date <= child_obj.education_allowance_end_date:
                        is_date_valid = True

                if is_date_valid:
                    matched_rule = rule
                    break

            if matched_rule:
                amount = matched_rule.amount

                if child_obj.allowance_supplementary_eligible:
                    amount += matched_rule.amount_supplementary

                if amount > 0:
                    if self.paid_by_fcf:
                        allowance_input = child_allowance_input_fcf if matched_rule.allowance_type == 'child' else education_allowance_input_fcf
                    else:
                        allowance_input = child_allowance_input if matched_rule.allowance_type == 'child' else education_allowance_input

                    input_values.append({
                        'amount': amount,
                        'input_type_id': allowance_input.id
                    })

        return input_values

class L10nChCafScale(models.Model):
    _name = 'l10n.ch.caf.scale'
    _description = 'Swiss Family Allowance Scale'
    _order = 'min_child_rank asc, min_age asc'

    fund_id = fields.Many2one('l10n.ch.compensation.fund', required=True, ondelete='cascade')

    min_age = fields.Integer(string="Min Age", default=0)
    max_age = fields.Integer(string="Max Age", default=16)

    allowance_type = fields.Selection(
        selection=[('child', 'Child Allowance'),
                   ('education', 'Education Allowance')],
        default='child',
        required=True,
        string="Type"
    )

    min_child_rank = fields.Integer(
        string="From Child",
        default=1,
        required=True,
        help="This quantity defines from which child this amount will apply."
    )

    amount = fields.Float(string="Monthly Amount", required=True)

    amount_supplementary = fields.Float(
        string="Supplementary Amount",
        help="Voluntary/Supplementary amount paid if configured on the child."
    )
