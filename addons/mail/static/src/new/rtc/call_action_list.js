/* @odoo-module */

import { Component } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { isMobileOS } from "@web/core/browser/feature_detection";

export class CallActionList extends Component {
    static props = ["thread", "fullscreen", "compact?"];
    static template = "mail.CallActionList";

    setup() {
        this.rtc = useRtc();
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
