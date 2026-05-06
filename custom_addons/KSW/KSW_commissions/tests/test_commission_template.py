"""Tests for ksw.commission.template — line application, employee assignment.

Covers:
  • Template created with line_ids
  • _apply_to_sheet fills lines onto an empty sheet
  • _apply_to_sheet is idempotent (no duplicates on re-apply)
  • _get_template_for_employee returns correct active template
  • Inactive template not returned by _get_template_for_employee
  • Employee can only be assigned to one template (ValidationError on second)
  • Adding employee to template auto-creates current-month sheet
  • New sheet has template lines pre-filled
  • Template without lines → _apply_to_sheet is a no-op
"""
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestCommissionTemplate(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # Categories
        cats = env['ksw.commission.category'].search([('code', 'in', [
            'location', 'mobile_phone', 'other',
        ])])
        cls.cat_loc = cats.filtered(lambda c: c.code == 'location')
        cls.cat_mob = cats.filtered(lambda c: c.code == 'mobile_phone')
        cls.cat_other = cats.filtered(lambda c: c.code == 'other')

        # Employees
        dept = env['hr.department'].create({'name': 'Tmpl Test Dept'})
        cls.emp1 = env['hr.employee'].sudo().create({
            'name': 'Tmpl Emp1', 'department_id': dept.id,
            'x_is_attendance_sheet': True,
        })
        cls.emp2 = env['hr.employee'].sudo().create({
            'name': 'Tmpl Emp2', 'department_id': dept.id,
            'x_is_attendance_sheet': True,
        })
        cls.emp3 = env['hr.employee'].sudo().create({
            'name': 'Tmpl Emp3', 'department_id': dept.id,
            'x_is_attendance_sheet': True,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _new_template(self, employees=None, lines=None, active=True):
        env = self.env
        tmpl = env['ksw.commission.template'].sudo().create({
            'name': 'Test Template',
            'active': active,
        })
        if lines:
            for ln in lines:
                env['ksw.commission.template.line'].sudo().create({
                    'template_id': tmpl.id,
                    **ln,
                })
        if employees:
            tmpl.sudo().write({
                'employee_ids': [(4, e.id) for e in employees],
            })
        return tmpl

    def _new_sheet(self, emp, period='2026-03-01'):
        return self.env['ksw.commission.sheet'].sudo().create({
            'employee_id': emp.id,
            'period': period,
        })

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_apply_to_sheet_fills_lines(self):
        """_apply_to_sheet populates an empty sheet with the template lines."""
        tmpl = self._new_template(lines=[
            {'category_id': self.cat_loc.id, 'amount': 300.0},
            {'category_id': self.cat_mob.id, 'amount': 150.0},
        ])
        sheet = self._new_sheet(self.emp1)
        # Remove any auto-applied lines from other templates.
        sheet.line_ids.sudo().unlink()
        tmpl._apply_to_sheet(sheet)
        amounts = sorted(sheet.line_ids.mapped('amount'))
        self.assertEqual(amounts, [150.0, 300.0])

    def test_02_apply_to_sheet_idempotent(self):
        """Calling _apply_to_sheet twice does not create duplicate lines."""
        tmpl = self._new_template(lines=[
            {'category_id': self.cat_loc.id, 'amount': 300.0},
        ])
        sheet = self._new_sheet(self.emp1, period='2026-02-01')
        sheet.line_ids.sudo().unlink()
        tmpl._apply_to_sheet(sheet)
        count_before = len(sheet.line_ids)
        tmpl._apply_to_sheet(sheet)   # second call
        self.assertEqual(len(sheet.line_ids), count_before)

    def test_03_get_template_for_employee_returns_assigned(self):
        """_get_template_for_employee returns the active template for an employee."""
        tmpl = self._new_template(employees=[self.emp2])
        found = self.env['ksw.commission.template']._get_template_for_employee(
            self.emp2)
        self.assertEqual(found, tmpl)

    def test_04_get_template_for_inactive_template_returns_empty(self):
        """An inactive template is not returned."""
        tmpl = self._new_template(employees=[self.emp3], active=False)
        found = self.env['ksw.commission.template']._get_template_for_employee(
            self.emp3)
        self.assertFalse(found)

    def test_05_employee_unique_template_constraint(self):
        """An employee already in template A cannot be added to template B."""
        emp = self.env['hr.employee'].sudo().create({
            'name': 'Tmpl Conflict Emp', 'x_is_attendance_sheet': True,
        })
        tmpl_a = self._new_template(employees=[emp])
        with self.assertRaises(ValidationError):
            self._new_template(employees=[emp])

    def test_06_template_without_lines_noop(self):
        """_apply_to_sheet on a template with no lines leaves the sheet empty."""
        tmpl = self.env['ksw.commission.template'].sudo().create({
            'name': 'Empty Tmpl',
        })
        sheet = self._new_sheet(self.emp1, period='2025-12-01')
        sheet.line_ids.sudo().unlink()
        tmpl._apply_to_sheet(sheet)
        self.assertEqual(len(sheet.line_ids), 0)

    def test_07_auto_create_sheet_on_employee_add(self):
        """Adding an employee to a template auto-creates a current-month sheet."""
        from odoo import fields
        emp = self.env['hr.employee'].sudo().create({
            'name': 'Tmpl Auto Sheet Emp', 'x_is_attendance_sheet': True,
        })
        tmpl = self.env['ksw.commission.template'].sudo().create({
            'name': 'Auto Sheet Test Tmpl',
            'active': True,
        })
        self.env['ksw.commission.template.line'].sudo().create({
            'template_id': tmpl.id,
            'category_id': self.cat_other.id,
            'amount': 100.0,
        })
        # Adding the employee triggers write() → _ensure_current_period_sheets
        tmpl.sudo().write({'employee_ids': [(4, emp.id)]})

        period = fields.Date.context_today(self.env['ksw.commission.sheet']).replace(day=1)
        sheet = self.env['ksw.commission.sheet'].sudo().search([
            ('employee_id', '=', emp.id),
            ('period', '=', period),
        ], limit=1)
        self.assertTrue(sheet, 'Expected auto-created sheet for current period.')
        # Template line should be pre-filled.
        self.assertTrue(sheet.line_ids, 'Expected template lines on auto-created sheet.')

    def test_08_apply_template_action_on_non_draft_raises(self):
        """action_apply_template raises UserError when sheet is not draft."""
        tmpl = self._new_template(lines=[
            {'category_id': self.cat_loc.id, 'amount': 200.0},
        ])
        emp = self.env['hr.employee'].sudo().create({
            'name': 'Apply Tmpl Confirmed Emp', 'x_is_attendance_sheet': True,
        })
        tmpl.sudo().write({'employee_ids': [(4, emp.id)]})
        sheet = self.env['ksw.commission.sheet'].sudo().search([
            ('employee_id', '=', emp.id),
        ], limit=1)
        if not sheet:
            sheet = self._new_sheet(emp, period='2025-09-01')
        sheet.sudo().action_confirm()
        from odoo.exceptions import UserError
        with self.assertRaises(UserError):
            sheet.sudo().action_apply_template()

    def test_09_employee_count_field(self):
        """employee_count is the number of employees assigned."""
        emp_a = self.env['hr.employee'].sudo().create({
            'name': 'EC Emp A', 'x_is_attendance_sheet': True,
        })
        emp_b = self.env['hr.employee'].sudo().create({
            'name': 'EC Emp B', 'x_is_attendance_sheet': True,
        })
        tmpl = self._new_template(employees=[emp_a, emp_b])
        self.assertEqual(tmpl.employee_count, 2)

