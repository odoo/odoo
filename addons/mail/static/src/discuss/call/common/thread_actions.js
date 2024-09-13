import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { CallSettings } from "@mail/discuss/call/common/call_settings";

import { useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";
import { CallConfirmation } from "./call_confirmation";

threadActionsRegistry
    .add("call", {
        condition(component) {
            return (
                component.thread?.allowCalls && !component.thread?.eq(component.rtc.state.channel)
            );
        },
        icon: "fa fa-fw fa-phone",
        iconLarge: "fa fa-fw fa-lg fa-phone",
        name: _t("Start a Call"),
        open(component, action) {
            if (!component.thread.rtcSessions.length) {
                action.popover.open(component.root.el.querySelector(`[name="${action.id}"]`), {
                    thread: component.thread,
                });
            } else {
                component.rtc.toggleCall(component.thread);
            }
        },
        panelOuterClass: "shadow-sm m-1",
        sequence: 10,
        setup(action) {
            const component = useComponent();
            component.rtc = useState(useService("discuss.rtc"));
            action.popover = usePopover(CallConfirmation, {
                onClose: () => action.close(),
                popoverClass: action.panelOuterClass,
            });
        },
    })
    .add("settings", {
        component: CallSettings,
        componentProps(action) {
            return { isCompact: true };
        },
        condition(component) {
            return (
                component.thread?.allowCalls &&
                (component.props.chatWindow?.isOpen || component.store.inPublicPage)
            );
        },
        icon: "fa fa-fw fa-gear",
        iconLarge: "fa fa-fw fa-lg fa-gear",
        name: _t("Show Call Settings"),
        nameActive: _t("Hide Call Settings"),
        sequence(component) {
            return component.props.chatWindow && component.thread?.eq(component.rtc.state.channel)
                ? 6
                : 60;
        },
        setup() {
            const component = useComponent();
            component.rtc = useState(useService("discuss.rtc"));
        },
        toggle: true,
    });
