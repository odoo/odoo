import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailFollowers extends models.ServerModel {
    _name = "mail.followers";

    _compute_display_name() {
        for (const record of this) {
            const [partner] = this.env["res.partner"].browse(record.partner_id);
            record.display_name = partner.display_name;
        }
    }

    _to_store(store, fields) {
        const kwargs = getKwArgs(arguments, "store", "fields");
        store = kwargs.store;
        fields = kwargs.fields;

        store._add_record_fields(
            this,
            fields.filter((field) => field !== "subtype_ids")
        );

        for (const follower of this) {
            const data = {};
            if (fields.includes("subtype_ids")) {
                data.subtype_ids = mailDataHelpers.Store.many(
                    this.env["mail.message.subtype"].browse(follower.subtype_ids)
                );
            }
            if (Object.keys(data).length) {
                store._add_record_fields(this.browse(follower.id), data);
            }
        }
    }
    get _to_store_defaults() {
        return [
            "display_name",
            "email",
            "is_active",
            "name",
            mailDataHelpers.Store.one("partner_id"),
            mailDataHelpers.Store.attr("thread", (follower) =>
                mailDataHelpers.Store.one(
                    this.env[follower.res_model].browse(follower.res_id),
                    makeKwArgs({ as_thread: true, only_id: true })
                )
            ),
        ];
    }
}
