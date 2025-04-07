import { Record } from "@mail/core/common/record";

export class HrEmployee extends Record {
    static _name = "hr.employee";
    static id = "id";

    /** @type {number} */
    id;
}

HrEmployee.register();
