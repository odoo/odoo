/** @odoo-module **/

import { addFakeModel, addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch(['hr.employee.public']);

addFakeModel('m2x.avatar.employee', {
    employee_id: { string: "Employee", type: 'many2one', relation: 'hr.employee.public' },
    employee_ids: { string: "Employees", type: "many2many", relation: 'hr.employee.public' },
});
