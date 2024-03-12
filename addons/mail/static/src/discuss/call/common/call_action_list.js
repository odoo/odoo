import { Component, useState } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class CallActionList extends Component {
    static components = { Dropdown, DropdownItem };
    static props = ["thread", "fullscreen", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        super.setup();
        this.rtc = useState(useService("discuss.rtc"));
        this.multiTab = useService("multi_tab");
    }

    get MORE() {
        return _t("More");
    }

    get moreActions() {
        const acts = [];
        acts.push({
            id: "raiseHand",
            name: !this.rtcState.selfSession.raisingHand ? _t("Raise Hand") : _t("Lower Hand"),
            icon: "fa fa-fw fa-hand-paper-o",
            onSelect: (ev) => this.onClickCallAction("raiseHand", ev),
        });
        if (isMobileOS && (this.rtcState.sendScreen || this.isOfActiveCall)) {
            acts.push({
                id: "shareScreen",
                name: !this.rtcState.sendScreen ? _t("Share Screen") : _t("Stop Sharing Screen"),
                icon: "fa fa-fw fa-desktop",
                onSelect: (ev) => this.onClickCallAction('screen', ev),
            });
        }
        if (!this.props.fullscreen.isActive) {
            acts.push({
                id: "fullScreen",
                name: _t("Enter Full Screen"),
                icon: "fa fa-fw fa-arrows-alt",
                onSelect: () => this.props.fullscreen.enter(),
            });
        } else {
            acts.push({
                id: "exitFullScreen",
                name: _t("Exit Full Screen"),
                icon: "fa fa-fw fa-compress",
                onSelect: () => this.props.fullscreen.exit(),
            });
        }
        return acts;
    }

    get isOfActiveCall() {
        return Boolean(this.props.thread.eq(this.rtc.state?.channel));
    }

    get isSmall() {
        return Boolean(this.props.compact && !this.props.fullscreen.isActive);
    }

    get isMobileOS() {
        return isMobileOS();
    }

    get rtcState() {
        return this.isOfActiveCall ? this.rtc.state : this.rtc.sharedState;
    }

    /**
     * @param {String} type
     * @param {MouseEvent} ev
     */
    async onClickCallAction(type, ev) {
        if (!this.isOfActiveCall) {
            this.multiTab.broadcast("discuss.rtc/toggle", { type });
        } else {
            await this.rtc.callActionByType(type);
        }
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickRejectCall(ev) {
        if (this.rtc.state.hasPendingRequest) {
            return;
        }
        await this.rtc.leaveCall(this.props.thread);
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickToggleAudioCall(ev) {
        const isActive = this.isOfActiveCall || this.rtc.sharedState.channelId;
        if (isActive) {
            this.multiTab.broadcast("discuss.rtc/leaveCall", {
                id: this.props.thread.id,
                model: this.props.thread.model,
            });
        }
        if (!isActive || this.isOfActiveCall) {
            await this.rtc.toggleCall(this.props.thread);
        }
    }
}
