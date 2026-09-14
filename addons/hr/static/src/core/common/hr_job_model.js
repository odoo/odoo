import { Record } from "@mail/model/export";

export class HrJob extends Record {
    static _name = "hr.job";

    /** @type {number} */
    id;
    /** @type {string} */
    name;
}

HrJob.register();
