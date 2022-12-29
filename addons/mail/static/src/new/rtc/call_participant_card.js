/* @odoo-module */

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { CallParticipantVideo } from "@mail/new/rtc/call_participant_video";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@mail/new/utils/misc";

export class CallParticipantCard extends Component {
    static props = ["session", "className", "minimized?"];
    static components = { CallParticipantVideo };
    static template = "mail.call_participant_card";

    setup() {
        this.rtc = useRtc();
        this.user = useService("user");
        onMounted(() => {
            this.rtc.updateVideoDownload(this.props.session, {
                viewCountIncrement: 1,
            });
        });
        onWillUnmount(() => {
            this.rtc.updateVideoDownload(this.props.session, {
                viewCountIncrement: -1,
            });
        });
    }

    get isOfActiveCall() {
        return Boolean(this.props.session.channelId === this.rtc.state.channel?.id);
    }

    get showConnectionState() {
        return Boolean(
            this.isOfActiveCall &&
                !(this.props.session.channelMember?.persona.id === this.user.partnerId) &&
                !["connected", "completed"].includes(this.props.session.connectionState)
        );
    }

    get name() {
        return this.props.session.channelMember?.persona.name;
    }

    get hasVideo() {
        return Boolean(this.props.session.videoStream);
    }

    get isTalking() {
        return Boolean(
            this.props.session && this.props.session.isTalking && !this.props.session.isMute
        );
    }

    onClick(ev) {
        if (isEventHandled(ev, "CallParticipantCard.clickVolumeAnchor")) {
            return;
        }
        if (this.props.session) {
            const channel = this.props.session.channel;
            if (channel.activeRtcSession === this.props.session) {
                channel.activeRtcSession = undefined;
            } else {
                channel.activeRtcSession = this.props.session;
            }
            return;
        }
        // TODO else if invitation => cancel invitation
    }

    onContextMenu() {
        return; // TODO redirect click to volume menu anchor
    }

    onClickVolumeAnchor(ev) {
        markEventHandled(ev, "CallParticipantCard.clickVolumeAnchor");
        // TODO volume popover
    }
}
