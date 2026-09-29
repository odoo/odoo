import { Record, fields } from "@mail/model/export";

export class HrEmployeePublic extends Record {
    static _name = "hr.employee.public";

    /** @type {number} */
    id;
    employee_id = fields.One("hr.employee");
    employee_skill_ids = fields.Many("hr.employee.skill");
}

HrEmployeePublic.register();
