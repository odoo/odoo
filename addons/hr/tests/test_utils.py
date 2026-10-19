def get_admin_employee(env, additional_values=None):
    """ Get `hr.employee_admin` or create it if it doesn't exist (singleton). """
    additional_values = additional_values or {}
    admin_employee = env.ref('hr.employee_admin', raise_if_not_found=False)
    if admin_employee:
        admin_employee.write(additional_values)
        return admin_employee
    return env['hr.employee'].create({
        'name': 'Mitchell Admin',
        'user_id': env.ref('base.user_admin').id,
        'department_id': env.ref('hr.dep_administration').id,
        'address_id': env.ref('base.main_partner').id,
        'structure_type_id': env.ref('hr.structure_type_employee').id,
        'company_id': env.ref('base.main_company').id,
        **additional_values,
    })
