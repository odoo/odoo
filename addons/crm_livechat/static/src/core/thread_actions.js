import { LivechatCommandDialog } from "@im_livechat/core/common/livechat_command_dialog";

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry.add("create-lead", {
    actionPanelComponent: LivechatCommandDialog,
    actionPanelComponentProps: (component, action) => ({
        close: () => action.close(),
        commandName: "lead",
        placeholderText: _t("e.g. Product pricing"),
        title: _t("Create Lead"),
        icon: "fa fa-handshake-o",
    }),
    close: (component, action) => action.popover?.close(),
    condition: (component) => false,
    panelOuterClass: "bg-100",
    icon: "fa fa-handshake-o",
    iconLarge: "fa-lg fa fa-handshake-o",
    name: _t("Create Lead"),
    sequence: 10,
    sequenceGroup: 25,
    setup(component) {
        if (!component.env.inChatWindow) {
            this.popover = usePopover(LivechatCommandDialog, {
                onClose: () => this.close(),
                popoverClass: this.panelOuterClass,
            });
        }
    },
    toggle: true,
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            thread: component.thread,
            ...action.actionPanelComponentProps,
        });
    },
});
