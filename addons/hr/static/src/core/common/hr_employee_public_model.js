import { Record, fields } from "@mail/model/export";

export class HrEmployeePublic extends Record {
    /** @type {"hr.employee.public"} */
    static _name = "hr.employee.public";

    /** @type {number} */
    id;
    employee_id = fields.One("hr.employee");
}

HrEmployeePublic.register();
