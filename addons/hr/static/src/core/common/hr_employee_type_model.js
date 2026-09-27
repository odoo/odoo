import { Record } from "@mail/model/export";

export class HrEmployeeType extends Record {
    static _name = "hr.employee.type";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

HrEmployeeType.register();
