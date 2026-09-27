import { fields, Record } from "@mail/model/export";

export class CalendarEvent extends Record {
    static _name = "calendar.event";
    /** @type {number} */
    id;
    /** @type {String} */
    name;
    /** @type {String} */
    location;
    /** @type {String} */
    videocall_location;
    start = fields.Datetime();
    stop = fields.Datetime();
    partner_ids = fields.Many("res.partner");
}
CalendarEvent.register();
