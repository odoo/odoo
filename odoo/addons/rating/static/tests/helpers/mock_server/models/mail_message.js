/** @odoo-module **/

import '@mail/../tests/helpers/mock_server/models/mail_message'; // ensure mail overrides are applied first

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    _mockMailMessageMessageFormat(ids) {
        const formattedMessages = super._mockMailMessageMessageFormat(...arguments);
        for (const formattedMessage of formattedMessages) {
            const [rating] = this.getRecords('rating.rating', [
                ['message_id', '=', formattedMessage.id],
            ]);
            if (rating) {
                formattedMessage['rating'] = {
                    'id': rating.id,
                    'ratingImageUrl': rating.rating_image_url,
                    'ratingText': rating.rating_text,
                };
            }
        }
        return formattedMessages;
    },
});
