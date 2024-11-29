import { mailModels } from "@mail/../tests/mail_test_helpers";
import { mailDataHelpers } from "@mail/../tests/mock_server/mail_mock_server";

import { getKwArgs } from "@web/../tests/web_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _to_store(ids, store, fields, for_current_user, follower_by_message_partner) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "store",
            "fields",
            "for_current_user",
            "follower_by_message_partner"
        );
        ids = kwargs.ids;
        store = kwargs.store;
        fields = kwargs.fields;
        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];
        if (!fields) {
            fields = ["rating_id"];
        }
        super._to_store(...arguments);
        for (const message of MailMessage.browse(ids)) {
            const [ratingId] = this.env["rating.rating"].search([["message_id", "=", message.id]]);
            store.add(this.browse(message.id), {
                rating_id: mailDataHelpers.Store.one(this.env["rating.rating"].browse(ratingId)),
            });
        }
    }
}
