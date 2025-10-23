import { ChatbotScriptStep } from "@mail/core/common/model_definitions";

import { patch } from "@web/core/utils/patch";

patch(ChatbotScriptStep.prototype, {
    setup() {
        super.setup(...arguments);
        this.isLast = false;
    },
});
