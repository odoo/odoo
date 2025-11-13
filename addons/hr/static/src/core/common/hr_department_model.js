import { Record } from "@mail/model/export";

export class HrDepartment extends Record {
    static _name = "hr.department";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

HrDepartment.register();
