import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { CallSettings } from "@mail/discuss/call/common/call_settings";

import { useComponent } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

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
        open(component) {
            component.rtc.toggleCall(component.thread);
        },
        sequence: 10,
        sequenceQuick: 30,
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
        },
    })
    .add("camera-call", {
        condition(component) {
            return (
                component.thread?.allowCalls && !component.thread?.eq(component.rtc.state.channel)
            );
        },
        icon: "fa fa-fw fa-video-camera",
        iconLarge: "fa fa-fw fa-lg fa-video-camera",
        name: _t("Start a Video Call"),
        open(component) {
            component.rtc.toggleCall(component.thread, { camera: true });
        },
        sequence: 5,
        sequenceQuick: (component) => (component.env.inDiscussApp ? 25 : 35),
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
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
        name: _t("Call Settings"),
        sequence: 20,
        sequenceGroup: 30,
        setup() {
            const component = useComponent();
            component.rtc = useService("discuss.rtc");
        },
        toggle: true,
    });
