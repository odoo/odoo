import { Record } from "@mail/model/export";

export class HrDepartment extends Record {
    static _name = "hr.department";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

HrDepartment.register();
