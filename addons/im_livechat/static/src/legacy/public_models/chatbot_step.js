/** @odoo-module **/

import { attr, one, Model } from "@im_livechat/legacy/model";

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
