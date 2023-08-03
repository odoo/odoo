/* @odoo-module */

import { useComponent, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

registry.category("mail.thread/actions").add("restart", {
    condition(component) {
        return component.chatbotService.canRestart;
    },
    icon: "fa fa-fw fa-refresh",
    name: _t("Restart Conversation"),
    open(component) {
        component.chatbotService.restart();
        component.chatWindowService.show(component.props.chatWindow);
    },
    sequence: 99,
    setup() {
        const component = useComponent();
        component.chatbotService = useState(useService("im_livechat.chatbot"));
        component.chatWindowService = useService("mail.chat_window");
    },
});
