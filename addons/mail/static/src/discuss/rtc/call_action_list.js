/* @odoo-module */

import { useRtc } from "@mail/discuss/rtc/rtc_hook";
import { Component } from "@odoo/owl";
import { isMobileOS } from "@web/core/browser/feature_detection";
import { useService } from "@web/core/utils/hooks";

export class CallActionList extends Component {
    static props = ["channel", "fullscreen", "compact?"];
    static template = "mail.CallActionList";

    setup() {
        this.rtc = useRtc();
        this.discussStore = useService("discuss.store");
    }

    get isOfActiveCall() {
        return Boolean(this.props.channel.id === this.rtc.state?.channel?.id);
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
        await this.rtc.leaveCall(this.props.channel);
    }

    /**
     * @param {MouseEvent} ev
     */
    async onClickToggleAudioCall(ev) {
        await this.rtc.toggleCall(this.props.channel);
    }
}
