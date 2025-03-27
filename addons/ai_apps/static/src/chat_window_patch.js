import { ChatWindow } from "@mail/core/common/chat_window";

import { useChildSubEnv } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";


patch(ChatWindow.prototype, {
    setup(){
        super.setup();
        let composerText;
        if (this.thread?.messages.length === 0) {
            composerText = this.props.chatWindow.composerText;
        } else {
            composerText = "";
        }
        useChildSubEnv({
            specialActions: this.props.chatWindow.specialActions,
            composerPreText: composerText,
            chatCaller: this.props.chatWindow.chatCaller,
        })
    },
    get style() {
        const res = super.style;
        return res + ' z-index: 1057;';
    }
});
