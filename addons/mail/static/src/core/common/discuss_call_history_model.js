import { fields, Record } from "@mail/model/export";

export class DiscussCallHistory extends Record {
    static _name = "discuss.call.history";

    /** @type {number} */
    id;
    end_dt = fields.Datetime();
    /** @type {number|undefined} */
    duration_hour;
    /** @type {boolean|undefined} */
    has_audio;
    /** @type {boolean|undefined} */
    has_recording;
    /** @type {boolean|undefined} */
    has_video;
}
DiscussCallHistory.register();
