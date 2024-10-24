import { ChatbotScript } from "@im_livechat/core/common/chatbot_script_model";
import { Record } from "@mail/core/common/record";

import { patch } from "@web/core/utils/patch";

patch(ChatbotScript.prototype, {
    setup() {
        super.setup();
        this.isLivechatTourRunning = false;
        this.welcomeSteps = Record.many("chatbot.script.step");
        this.partner = Record.one("Persona");
    },
});
