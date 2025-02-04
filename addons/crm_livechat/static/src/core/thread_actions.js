import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import "@mail/discuss/call/common/thread_actions";
import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { CreateLeadPanel } from "./create_lead_panel";

threadActionsRegistry.add("create-lead", {
    close(component, action) {
        action.popover?.close();
    },
    component: CreateLeadPanel,
    componentProps(action) {
        return { close: () => action.close() };
    },
    condition(component) {
        return (
            component.thread &&
            (component.thread.channel_type === "livechat" ||
                component.thread.channel_type === "whatsapp")
        );
    },
    panelOuterClass: "bg-100",
    icon: "fa fa-handshake-o",
    iconLarge: "fa-lg fa fa-handshake-o",
    name: _t("Create lead"),
    sequence: 20,
    sequenceGroup: 50,
    setup(action) {
        const component = useComponent();
        if (!component.props.chatWindow) {
            action.popover = usePopover(CreateLeadPanel, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        }
    },
    toggle: true,
    open(component, action) {
        action.popover?.open(component.root.el.querySelector(`[name="${action.id}"]`), {
            thread: component.thread,
        });
    },
});
