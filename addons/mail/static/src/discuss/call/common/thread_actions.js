import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { CallSettings } from "@mail/discuss/call/common/call_settings";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

threadActionsRegistry
    .add("call", {
        condition(component) {
            return component.thread?.allowCalls && !component.thread?.eq(component.rtc.channel);
        },
        icon: "fa fa-fw fa-phone text-success",
        iconLarge: "fa fa-fw fa-lg fa-phone text-success",
        name(component) {
            if (component.thread.rtc_session_ids.length > 0) {
                return _t("Join the Call");
            }
            return _t("Start Call");
        },
        nameClass: "text-success",
        open(component) {
            component.rtc.toggleCall(component.thread);
        },
        sequence: 10,
        sequenceQuick: 30,
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
        },
        sidebarSequence: 10,
        sidebarSequenceGroup: 10,
    })
    .add("camera-call", {
        condition(component) {
            return component.thread?.allowCalls && !component.thread?.eq(component.rtc.channel);
        },
        icon: "fa fa-fw fa-video-camera text-success",
        iconLarge: "fa fa-fw fa-lg fa-video-camera text-success",
        name(component) {
            if (component.thread.rtc_session_ids.length > 0) {
                return _t("Join the Call with Camera");
            }
            return _t("Start Video Call");
        },
        nameClass: "text-success",
        open(component) {
            component.rtc.toggleCall(component.thread, { camera: true });
        },
        sequence: 5,
        sequenceQuick: (component) => (component.env.inDiscussApp ? 25 : 35),
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
        },
        sidebarSequence: 20,
        sidebarSequenceGroup: 10,
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
        name: _t("Call Settings"),
        sequence: 20,
        sequenceGroup: 30,
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
        },
        toggle: true,
    })
    .add("disconnect", {
        condition: (component) => component.rtc.selfSession?.in(component.thread?.rtc_session_ids),
        open: (component) => component.rtc.toggleCall(component.thread),
        icon: "fa fa-fw fa-phone text-danger",
        iconLarge: "fa fa-fw fa-lg fa-phone text-danger",
        name: _t("Disconnect"),
        nameClass: "text-danger",
        partition: false,
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
        },
        sidebarSequence: 30,
        sidebarSequenceGroup: 10,
    });
