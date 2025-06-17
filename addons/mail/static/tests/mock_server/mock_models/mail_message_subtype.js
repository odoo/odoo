import { fields, getKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailMessageSubtype extends models.ServerModel {
    _name = "mail.message.subtype";

    default = fields.Generic({ default: true });
    subtype_xmlid = fields.Char();

    _records = [
        {
            default: false,
            internal: true,
            name: "Activities",
            sequence: 100,
            subtype_xmlid: "mail.mt_activities",
        },
        {
            default: false,
            internal: true,
            name: "Notes",
            sequence: 90,
            subtype_xmlid: "mail.mt_note",
            track_recipients: true,
        },
        {
            name: "Messages",
            sequence: 0,
            subtype_xmlid: "mail.mt_comment",
            track_recipients: true,
        },
    ];

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        ids = kwargs.ids;
        store = kwargs.store;
        fields = kwargs.fields ?? [];

        for (const subtypeId of ids) {
            store.add(this.browse(subtypeId), this._read_format(subtypeId, fields, false)[0]);
        }
    }
}
