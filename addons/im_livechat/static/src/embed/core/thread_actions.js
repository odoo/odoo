/* @odoo-module */

import { showChatWindow } from "@mail/core/common/chat_window_service";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

registry.category("mail.thread/actions").add("restart", {
    condition(component) {
        return component.chatbotService.canRestart;
    },
    icon: "fa fa-fw fa-refresh",
    name: _t("Restart Conversation"),
    open(component) {
        component.chatbotService.restart();
        showChatWindow(component.props.chatWindow);
    },
    sequence: 99,
});
