import { LivechatCommandDialog } from "@im_livechat/core/common/livechat_command_dialog";

import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";

threadActionsRegistry.add("create-lead", {
    close: (component, action) => action.popover?.close(),
    component: LivechatCommandDialog,
    componentProps: (component, action) => ({
        close: () => action.close(),
        commandName: "lead",
        placeholderText: _t("e.g. Product pricing"),
        title: _t("Create Lead"),
        icon: "fa fa-handshake-o",
    }),
    condition: (component) => false,
    panelOuterClass: "bg-100",
    icon: "fa fa-handshake-o",
    iconLarge: "fa-lg fa fa-handshake-o",
    name: _t("Create Lead"),
    sequence: 10,
    sequenceGroup: 25,
    setup(action) {
        const component = useComponent();
        if (!component.env.inChatWindow) {
            action.popover = usePopover(LivechatCommandDialog, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        }
    },
    toggle: true,
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            thread: component.thread,
            ...action.componentProps,
        });
    },
});
