/* @odoo-module */

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
        this.rtc = useState(useService("discuss.rtc"));
    }

    get MORE() {
        return _t("More");
    }

    get moreActions() {
        const acts = [];
        acts.push({
            id: "raiseHand",
            name: !this.rtc.state?.selfSession.raisingHand ? _t("Raise Hand") : _t("Lower Hand"),
            icon: "fa fa-fw fa-hand-paper-o",
            onSelect: (ev) => this.onClickRaiseHand(ev),
        });
        if (!isMobileOS()) {
            acts.push({
                id: "shareScreen",
                name: !this.rtc.state.sendScreen ? _t("Share Screen") : _t("Stop Sharing Screen"),
                icon: "fa fa-fw fa-desktop",
                onSelect: () => this.rtc.toggleVideo("screen"),
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

    /**
     * @param {MouseEvent} ev
     */
    async onClickDeafen(ev) {
        if (this.rtc.state.selfSession.isDeaf) {
            this.rtc.undeafen();
        } else {
            this.rtc.deafen();
        }
    }

    async onClickRaiseHand(ev) {
        this.rtc.raiseHand(!this.rtc.state.selfSession.raisingHand);
    }

    /**
     * @param {MouseEvent} ev
     */
    onClickMicrophone(ev) {
        if (this.rtc.state.selfSession.isMute) {
            if (this.rtc.state.selfSession.isSelfMuted) {
                this.rtc.unmute();
            }
            if (this.rtc.state.selfSession.isDeaf) {
                this.rtc.undeafen();
            }
        } else {
            this.rtc.mute();
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
        await this.rtc.toggleCall(this.props.thread);
    }
}
