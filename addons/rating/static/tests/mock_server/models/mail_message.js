import { mailModels } from "@mail/../tests/mail_test_helpers";

import { getKwArgs } from "@web/../tests/web_test_helpers";


export class MailMessage extends mailModels.MailMessage {
    _to_store(ids, store, for_current_user, follower_by_message_partner) {
        const kwargs = getKwArgs(
            arguments,
            "ids",
            "store",
            "for_current_user",
            "follower_by_message_partner"
        );
        ids = kwargs.ids;
        store = kwargs.store;

        /** @type {import("mock_models").MailMessage} */
        const MailMessage = this.env["mail.message"];

        super._to_store(...arguments);
        const messages = MailMessage._filter([["id", "in", ids]]);
        for (const message of messages) {
            const [rating] = this.env["rating.rating"]._filter([["message_id", "=", message.id]]);
            if (rating) {
                store.add("Message", {
                    id: message.id,
                    rating: {
                        id: rating.id,
                        ratingImageUrl: rating.rating_image_url,
                        ratingText: rating.rating_text,
                    },
                });
            }
        }
    }
}
