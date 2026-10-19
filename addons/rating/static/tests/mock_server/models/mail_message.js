import { mailModels } from "@mail/../tests/mail_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _store_message_fields(res) {
        /** @type {import("mock_models").RatingRating} */
        const RatingRating = this.env["rating.rating"];

        super._store_message_fields(res);
        // sudo: mail.message - guest and portal user can receive rating of accessible message
        res.one("rating_id", "_store_rating_fields", {
            sudo: true,
            value: (m) => {
                const [ratingId] = RatingRating.search([["message_id", "=", m.id]]);
                return RatingRating.browse(ratingId);
            },
        });
    }
}
