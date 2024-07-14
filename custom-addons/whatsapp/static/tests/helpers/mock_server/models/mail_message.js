/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    _mockMailMessageMessageFormat(ids) {
        const formattedMessages = super._mockMailMessageMessageFormat(...arguments);
        for (const formattedMessage of formattedMessages) {
            const [whatsappMessage] = this.getRecords("whatsapp.message", [
                ["mail_message_id", "=", formattedMessage.id],
            ]);
            if (whatsappMessage) {
                formattedMessage["whatsappStatus"] = whatsappMessage.state;
            }
        }
        return formattedMessages;
    },
});
