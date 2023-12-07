/** @odoo-module **/

import { addFakeModel, addModelNamesToFetch } from '@bus/../tests/helpers/model_definitions_helpers';

addModelNamesToFetch(['hr.employee', 'hr.skill', 'hr.employee.skill']);

addFakeModel('m2o.avatar.employee', {
    employee_id: { string: "Employee", type: 'many2one', relation: 'hr.employee' },
});
