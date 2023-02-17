/** @odoo-module **/

import { attr, one, Model } from "@mail/model";

Model({
    name: "ChatbotStep",
    fields: {
        chabotOwner: one("Chatbot", {
            identifying: true,
            inverse: "currentStep",
        }),
        data: attr(),
    },
});
