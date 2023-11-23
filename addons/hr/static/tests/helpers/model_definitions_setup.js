/** @odoo-module **/

import { addFakeModel, addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch(['hr.employee.public', 'hr.department']);

addFakeModel('hr.employee', {
    department_id: { string: "Department", type: "many2one", relation: "hr.department" },
    job_title: { string: "Job title", type: "char" },
    work_email: { string: "Work email", type: "char" },
    work_phone: { string: "Work phone", type: "char" },
});
addFakeModel('m2x.avatar.employee', {
    employee_id: { string: "Employee", type: 'many2one', relation: 'hr.employee.public' },
    employee_ids: { string: "Employees", type: "many2many", relation: 'hr.employee.public' },
});
