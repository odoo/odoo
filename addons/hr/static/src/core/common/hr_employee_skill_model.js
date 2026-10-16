import { Record } from "@mail/model/export";

export class HrEmployeeSkill extends Record {
    static _name = "hr.employee.skill";

    /** @type {number} */
    id;
    /** @type {string} */
    color;
    /** @type {string} */
    display_name;
}

HrEmployeeSkill.register();
