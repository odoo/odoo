import { Record } from "@mail/model/export";

export class HrWorkLocation extends Record {
    static _name = "hr.work.location";

    /** @type {number} */
    id;
    /** @type {string} */
    location_type;
    /** @type {string} */
    name;
}

HrWorkLocation.register();
