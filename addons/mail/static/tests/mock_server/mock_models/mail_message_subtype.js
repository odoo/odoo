import { fields, models } from "@web/../tests/web_test_helpers";

export class MailMessageSubtype extends models.ServerModel {
    _name = "mail.message.subtype";

    default = fields.Generic({ default: true });
    subtype_xmlid = fields.Char();

    _records = [
        {
            default: false,
            internal: true,
            name: "Activities",
            sequence: 90,
            subtype_xmlid: "mail.mt_activities",
        },
        {
            default: false,
            internal: true,
            name: "Note",
            sequence: 100,
            subtype_xmlid: "mail.mt_note",
            track_recipients: true,
        },
        {
            name: "Discussions",
            sequence: 0,
            subtype_xmlid: "mail.mt_comment",
            track_recipients: true,
        },
    ];
}
