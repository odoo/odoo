import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { getKwArgs, makeKwArgs, models } from "@web/../tests/web_test_helpers";

export class MailFollowers extends models.ServerModel {
    _name = "mail.followers";

    /* override */
    _compute_display_name() {
        for (const record of this) {
            const [partner] = this.env["res.partner"].browse(record.partner_id);
            record.display_name = partner.display_name;
        }
    }

    _to_store(ids, store, fields) {
        const kwargs = getKwArgs(arguments, "ids", "store", "fields");
        fields = kwargs.fields;

        /** @type {import("mock_models").MailFollowers} */
        const MailFollowers = this.env["mail.followers"];
        /** @type {import("mock_models").ResPartner} */
        const ResPartner = this.env["res.partner"];

        if (!fields) {
            fields = {
                display_name: true,
                email: true,
                is_active: true,
                name: true,
                partner_id: true,
                partner: null,
                thread: [],
            };
        }
        const followers = MailFollowers.browse(ids);
        for (const follower of followers) {
            const [data] = this._read_format(
                follower.id,
                Object.keys(fields).filter((field) => !["partner", "thread"].includes(field)),
                false
            );
            if ("partner" in fields) {
                data.partner = mailDataHelpers.Store.one(
                    ResPartner.browse(follower.partner_id),
                    makeKwArgs({ fields: fields.partner })
                );
            }
            if ("thread" in fields) {
                data.thread = mailDataHelpers.Store.one(
                    this.env[follower.res_model].browse(follower.res_id),
                    makeKwArgs({ as_thread: true, only_id: true })
                );
            }
            store.add(this.browse(follower.id), data);
        }
    }
}
