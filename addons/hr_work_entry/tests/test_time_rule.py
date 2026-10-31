# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('-at_install', 'post_install')
class TestTimeRuleConfiguration(TransactionCase):
    """The fields computed for the rule form and the checks of the rule configuration."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.belgium = cls.env.ref('base.be')
        # explicit country: hr_holidays defaults it to the company's one
        cls.generic_type = cls.env['hr.work.entry.type'].create({
            'name': 'Generic Time Rule Type',
            'code': 'TRGEN',
            'country_id': False,
        })
        cls.belgian_type = cls.env['hr.work.entry.type'].create({
            'name': 'Belgian Time Rule Type',
            'code': 'TRBE',
            'country_id': cls.belgium.id,
        })

    def _create_rule(self, **vals):
        return self.env['hr.time.rule'].create({
            'name': 'Configuration Rule',
            'condition_work_entry_type_ids': [self.generic_type.id],
            **vals,
        })

    def test_condition_label(self):
        schedule_rule = self._create_rule(working_hours_mode='schedule_day')
        self.assertEqual(schedule_rule.condition_label, '> schedule/day')

        fixed_hours_rule = self._create_rule(
            working_hours_mode='week',
            threshold_operator='less_than',
            expected_hours=38,
            timing_start=20,
            timing_stop=23.5,
        )
        self.assertEqual(fixed_hours_rule.condition_label, '< 38h/week 20:00-23:30')

    def test_country_work_entry_types(self):
        """A rule offers the types of its country, or the generic ones if its country has none."""
        belgian_rule = self._create_rule(country_id=self.belgium.id)
        self.assertIn(self.belgian_type, belgian_rule.country_work_entry_type_ids)
        self.assertNotIn(self.generic_type, belgian_rule.country_work_entry_type_ids)

        country_without_types = self.env.ref('base.aq')
        rule_without_localized_types = self._create_rule(country_id=country_without_types.id)
        self.assertIn(self.generic_type, rule_without_localized_types.country_work_entry_type_ids)
        self.assertNotIn(self.belgian_type, rule_without_localized_types.country_work_entry_type_ids)

    def test_country_follows_company(self):
        belgian_company = self.env['res.company'].create({'name': 'Belgian Company', 'country_id': self.belgium.id})
        rule = self._create_rule(company_id=belgian_company.id)
        self.assertEqual(rule.country_id, self.belgium)
        self.assertIn(self.belgian_type, rule.country_work_entry_type_ids)

    def test_copy_name(self):
        rule = self._create_rule()
        self.assertEqual(rule.copy().name, 'Configuration Rule (copy)')

    def test_invalid_employee_domain(self):
        with self.assertRaises(ValidationError):
            self._create_rule(employee_domain="[('name', '='")
