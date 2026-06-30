import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { getKwArgs, makeKwArgs } from "@web/../tests/web_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _to_store(store, fields, for_current_user, follower_by_message_partner) {
        const kwargs = getKwArgs(
            arguments,
            "store",
            "fields",
            "for_current_user",
            "follower_by_message_partner"
        );
        store = kwargs.store;
        fields = kwargs.fields;

        super._to_store(...arguments, makeKwArgs({ fields: fields.filter((field) => field !== "rating_id") }));
        if (!fields.includes("rating_id")) {
            return;
        }
        for (const message of this) {
            const [ratingId] = this.env["rating.rating"].search([["message_id", "=", message.id]]);
            store._add_record_fields(this.browse(message.id), {
                rating_id: mailDataHelpers.Store.one(this.env["rating.rating"].browse(ratingId)),
            });
        }
    }

    get _to_store_defaults() {
        return [...super._to_store_defaults, "rating_id"];
    }
}
