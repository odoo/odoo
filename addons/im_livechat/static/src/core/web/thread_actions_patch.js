import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { useComponent } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { TranscriptSenderPopover } from "./transcript_sender_popover";

threadActionsRegistry.add("send-conversation", {
    close(component, action) {
        action.popover?.close();
    },
    component: TranscriptSenderPopover,
    componentProps(action) {
        return { close: () => action.close() };
    },
    condition(component) {
        return component.thread?.channel_type === "livechat" && !component.thread.livechat_active;
    },
    icon: "fa fa-fw fa-paper-plane",
    iconLarge: "fa fa-fw fa-lg fa-paper-plane",
    panelOuterClass: "bg-100",
    name(component) {
        return component.props.chatWindow?.isOpen
            ? _t("Send conversation")
            : _t("Send a copy of the conversation");
    },
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            thread: component.thread,
        });
    },
    setup(action) {
        const component = useComponent();
        if (!component.props.chatWindow) {
            action.popover = usePopover(TranscriptSenderPopover, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        }
    },
    toggle: true,
    sequenceGroup(component) {
        return component.props.chatWindow?.isOpen ? 20 : 5;
    },
});
