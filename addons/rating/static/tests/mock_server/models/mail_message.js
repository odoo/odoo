import { mailModels } from "@mail/../tests/mail_test_helpers";

export class MailMessage extends mailModels.MailMessage {
    _message_format() {
        const formattedMessages = super._message_format(...arguments);
        for (const message of formattedMessages) {
            const [rating] = this.env["rating.rating"]._filter([["message_id", "=", message.id]]);
            if (rating) {
                message["rating"] = {
                    id: rating.id,
                    ratingImageUrl: rating.rating_image_url,
                    ratingText: rating.rating_text,
                };
            }
        }
        return formattedMessages;
    }
}
