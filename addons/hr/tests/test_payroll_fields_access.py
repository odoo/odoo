# Part of Odoo. See LICENSE file for full copyright and licensing details.

from lxml import etree

from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPayrollFieldsAccess(TransactionCase):
    def test_related_fields_on_version(self):
        """ Some groups have been added to avoid users with basic access to HR app see some critical (like wage field for instance)
            This test makes sure the groups added in version fields is also in the employee fields related.
            However, to define the same groups in employee fields, we have to redefine the related fields (readonly=False, related='version_id.{field_name})
            Otherwise, the field we loose the linked with the version field and could be readonly instead of editable.
        """
        version_fields = {
            f_name: field
            for f_name, field in self.env['hr.version']._fields.items()
            if field.groups and field.groups not in ['hr.group_hr_user', 'base.group_user'] and not (field.related and field.related.startswith('employee_id'))
        }
        employee_fields = {
            f_name: field
            for f_name, field in self.env['hr.employee']._fields.items()
            if f_name in version_fields
        }
        fields_without_group = []
        fields_without_related = []
        fields_readonly = []
        for f_name, field in employee_fields.items():
            v_field = version_fields[f_name]
            if not (field.groups and field.groups != v_field):
                fields_without_group.append(f_name)
            elif not (field.related and field.related == f'version_id.{f_name}'):
                fields_without_related.append(f_name)
            elif field.readonly != v_field.readonly:
                fields_readonly.append(f_name)
        self.assertFalse(fields_without_group, "Inconsistency between some employee fields and version ones (those employees fields should have the same groups than related one in version")
        self.assertFalse(fields_without_related, "Some employee fields have the same name than the version ones but they are not related")
        self.assertFalse(fields_readonly, "(Readonly) Inconsistency between some employee fields and version ones, the both fields (in version and employee) have to be readonly or editable")

    def _test_payroll_fields_are_hidden_to_non_payroll_users(self, model_name, view_id, payroll_page_name):
        form_view = self.env.ref(view_id)
        form_view_get_result = self.env['hr.employee'].get_view(form_view.id, 'form')
        form_view_arch = form_view_get_result['arch']
        node = etree.fromstring(form_view_arch)
        self.assertTrue(node.xpath(f"//page[@name='{payroll_page_name}']"), f"[{model_name}] Payroll page should be found in the form view.")
        payroll_field_node_list = node.xpath(f"//page[@name='{payroll_page_name}']//field[not(ancestor::field)]")
        self.assertTrue(payroll_field_node_list, f"[{model_name}] At least one field should be found inside Payroll information page.")
        payroll_field_names = [
            payroll_field_node.attrib['name']
            for payroll_field_node in payroll_field_node_list
        ]
        current_payroll_field_names = {
            f_name
            for f_name, field in self.env[model_name]._fields.items()
            if field.groups and ('hr.group_hr_manager' in field.groups or 'hr_payroll.group_hr_payroll_user' in field.groups)
        }
        whitelist_field_names = [
            'resource_calendar_id',
            'employee_type',
            'tz',
            'currency_id',
            'lang',
            'registration_number',
            'standard_calendar_id',
            'employee_age',
            'distance_home_work',
            'distance_home_work_unit',
            'show_billable_time_target',
            'billable_time_target',
            'holidays',
            'car_id',
            'new_car',
            'new_car_model_id',
            'ordered_car_id',
            'fuel_type',
            'transport_mode_bike',
            'bike_id',
            'new_bike',
            'new_bike_model_id',
            'originated_offer_id',
            'is_non_resident',
            'structure_id'
        ]
        missing_group_field_names = [
            f_name
            for f_name in payroll_field_names
            if f_name not in current_payroll_field_names and f_name not in whitelist_field_names
        ]
        self.assertFalse(
            missing_group_field_names,
            "[{}] Missing payroll group on following fields: \n - {}".format(
                model_name,
                '\n - '.join(missing_group_field_names),
            ),
        )

    def test_payroll_fields_are_hidden_to_non_payroll_users_in_employee_form_view(self):
        self._test_payroll_fields_are_hidden_to_non_payroll_users('hr.employee', 'hr.view_employee_form', 'payroll_information')

    def test_payroll_fields_are_hidden_to_non_payroll_users_in_version_form_view(self):
        self._test_payroll_fields_are_hidden_to_non_payroll_users('hr.version', 'hr.hr_contract_template_form_view', 'information')
