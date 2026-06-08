import { fields, Record } from "@mail/model/export";

export class ScheduledMessage extends Record {
    static _name = "mail.scheduled.message";

    /** @type {number} */
    id;
    attachment_ids = fields.Many("ir.attachment");
    author_id = fields.One("res.partner");
    body = fields.Html("");
    /** @type {boolean} */
    composition_batch;
    /** @type {boolean} */
    is_note;
    scheduled_date = fields.Datetime();
    thread = fields.One("mail.thread");
}

ScheduledMessage.register();
