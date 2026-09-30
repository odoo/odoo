import { Record } from "@mail/core/common/record";

export class HrDepartment extends Record {
    static _name = "hr.department";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

HrDepartment.register();
