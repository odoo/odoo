/* @odoo-module */

import { Component, onMounted, onWillUnmount } from "@odoo/owl";
import { useRtc } from "@mail/new/rtc/rtc_hook";
import { CallParticipantVideo } from "@mail/new/rtc/call_participant_video";
import { useService } from "@web/core/utils/hooks";
import { isEventHandled, markEventHandled } from "@mail/new/utils/misc";

export class CallParticipantCard extends Component {
    static props = ["className", "cardData", "thread", "minimized?"];
    static components = { CallParticipantVideo };
    static template = "mail.call_participant_card";

    setup() {
        this.rpc = useService("rpc");
        this.rtc = useRtc();
        this.threadService = useService("mail.thread");
        this.user = useService("user");
        onMounted(() => {
            if (!this.rtcSession) {
                return;
            }
            this.rtc.updateVideoDownload(this.rtcSession, {
                viewCountIncrement: 1,
            });
        });
        onWillUnmount(() => {
            if (!this.rtcSession) {
                return;
            }
            this.rtc.updateVideoDownload(this.rtcSession, {
                viewCountIncrement: -1,
            });
        });
    }

    get rtcSession() {
        return this.props.cardData.session;
    }

    get channelMember() {
        return this.rtcSession ? this.rtcSession.channelMember : this.props.cardData.member;
    }

    get isOfActiveCall() {
        return Boolean(this.rtcSession && this.rtcSession.channelId === this.rtc.state.channel?.id);
    }

    get showConnectionState() {
        return Boolean(
            this.isOfActiveCall &&
                !(this.rtcSession.channelMember?.persona.id === this.user.partnerId) &&
                !["connected", "completed"].includes(this.rtcSession.connectionState)
        );
    }

    get name() {
        return this.channelMember?.persona.name;
    }

    get hasVideo() {
        return Boolean(this.rtcSession?.videoStream);
    }

    get isTalking() {
        return Boolean(
            this.rtcSession && this.rtcSession.isTalking && !this.rtcSession.isMute
        );
    }

    async onClick(ev) {
        if (isEventHandled(ev, "CallParticipantCard.clickVolumeAnchor")) {
            return;
        }
        if (this.rtcSession) {
            const channel = this.rtcSession.channel;
            if (channel.activeRtcSession === this.rtcSession) {
                channel.activeRtcSession = undefined;
            } else {
                channel.activeRtcSession = this.rtcSession;
            }
            return;
        }
        const channelData = await this.rpc("/mail/rtc/channel/cancel_call_invitation", {
            channel_id: this.props.thread.id,
            member_ids: [this.channelMember.id],
        });
        this.threadService.update(this.props.thread, {
            serverData: {
                invitedMembers: channelData.invitedMembers,
            },
        });
    }

    onContextMenu() {
        return; // TODO redirect click to volume menu anchor
    }

    onClickVolumeAnchor(ev) {
        markEventHandled(ev, "CallParticipantCard.clickVolumeAnchor");
        // TODO volume popover
    }
}
