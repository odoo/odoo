import { fields, Record } from "@mail/core/common/record";

export class DiscussCallHistory extends Record {
    static id = "id";
    static _name = "discuss.call.history";

    /** @type {number} */
    id;
    end_dt = fields.Datetime();
    /** @type {number|undefined} */
    duration_hour;
}
DiscussCallHistory.register();
