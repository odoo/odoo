import { DataResponse } from "@mail/core/common/data_response_model";
import { patchModel } from "@mail/model/export";
import { fields } from "@mail/model/misc";

export const dataResponsePatch = patchModel(DataResponse, {
    setup() {
        super.setup(...arguments);
        this.chatbot_step = fields.One("ChatbotStep");
    },
});
