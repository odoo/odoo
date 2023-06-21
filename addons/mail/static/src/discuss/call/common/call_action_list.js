/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";

import { Component } from "@odoo/owl";

import { isMobileOS } from "@web/core/browser/feature_detection";

export class CallActionList extends Component {
    static props = ["thread", "fullscreen", "compact?"];
    static template = "discuss.CallActionList";

    setup() {
        this.rtc = useRtc();
        this.store = useStore();
    }

    get isOfActiveCall() {
        return Boolean(this.props.thread.id === this.rtc.state?.channel?.id);
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
