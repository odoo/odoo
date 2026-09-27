import { DataResponse } from "@mail/core/common/data_response_model";
import { fields } from "@mail/model/misc";

import { patch } from "@web/core/utils/patch";

patch(DataResponse.prototype, {
    setup() {
        super.setup(...arguments);
        this.chatbot_step = fields.One("ChatbotStep");
    },
});
