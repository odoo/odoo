import { SESSION_STATE } from "@im_livechat/embed/common/livechat_service";

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";
import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";

threadActionsRegistry.add("restart", {
    condition(component) {
        return component.chatbotService.canRestart;
    },
    icon: "fa fa-fw fa-refresh",
    name: _t("Restart Conversation"),
    open(component) {
        component.chatbotService.restart();
        component.props.chatWindow.open();
    },
    sequence: 99,
    sequenceQuick: 15,
});

const callSettingsAction = threadActionsRegistry.get("settings");
patch(callSettingsAction, {
    condition(component) {
        if (component.thread?.channel_type !== "livechat") {
            return super.condition(...arguments);
        }
        return (
            component.livechatService.state === SESSION_STATE.PERSISTED &&
            component.rtcService.state.channel?.eq(component.thread)
        );
    },
    setup() {
        super.setup(...arguments);
        const component = useComponent();
        component.livechatService = useService("im_livechat.livechat");
        component.rtcService = useService("discuss.rtc");
    },
});
