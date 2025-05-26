import { Record } from "@mail/core/common/record";

export class HrWorkLocation extends Record {
    static _name = "hr.work.location";
    static id = "id";

    /** @type {number} */
    id;
    /** @type {string} */
    location_type;
    /** @type {string} */
    name;
}

HrWorkLocation.register();
