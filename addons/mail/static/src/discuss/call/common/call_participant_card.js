/* @odoo-module */

import { useStore } from "@mail/core/common/messaging_hook";
import { CallContextMenu } from "@mail/discuss/call/common/call_context_menu";
import { CallParticipantVideo } from "@mail/discuss/call/common/call_participant_video";
import { useRtc } from "@mail/discuss/call/common/rtc_hook";
import { useHover } from "@mail/utils/common/hooks";
import { isEventHandled, markEventHandled } from "@web/core/utils/misc";

import { Component, onMounted, onWillUnmount, useRef } from "@odoo/owl";

import { usePopover } from "@web/core/popover/popover_hook";
import { useService } from "@web/core/utils/hooks";

const HIDDEN_CONNECTION_STATES = new Set(["connected", "completed"]);

export class CallParticipantCard extends Component {
    static props = ["className", "cardData", "thread", "minimized?"];
    static components = { CallParticipantVideo };
    static template = "discuss.CallParticipantCard";

    setup() {
        this.contextMenuAnchorRef = useRef("contextMenuAnchor");
        this.popover = usePopover(CallContextMenu);
        this.rpc = useService("rpc");
        this.rtc = useRtc();
        this.store = useStore();
        this.rootHover = useHover("root");
        this.threadService = useService("mail.thread");
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

    get isContextMenuAvailable() {
        if (!this.rtcSession) {
            return false;
        }
        return this.rtcSession?.id !== this.rtc.state.selfSession?.id;
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
                !(this.rtcSession.channelMember?.persona.localId === this.store.self?.localId) &&
                !HIDDEN_CONNECTION_STATES.has(this.rtcSession.connectionState)
        );
    }

    get name() {
        return this.channelMember?.persona.name;
    }

    get hasMediaError() {
        return (
            this.isOfActiveCall &&
            Boolean(this.rtcSession?.videoError || this.rtcSession?.audioError)
        );
    }

    get hasVideo() {
        return Boolean(this.rtcSession?.videoStream);
    }

    get isTalking() {
        return Boolean(this.rtcSession && this.rtcSession.isTalking && !this.rtcSession.isMute);
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
            invitedMembers: channelData.invitedMembers,
        });
    }

    async onClickReplay() {
        this.env.bus.trigger("RTC-SERVICE:PLAY_MEDIA");
    }

    /**
     * @param {Event} ev
     */
    onContextMenu(ev) {
        ev.preventDefault();
        markEventHandled(ev, "CallParticipantCard.clickVolumeAnchor");
        if (this.popover.isOpen) {
            this.popover.close();
            return;
        }
        if (!this.contextMenuAnchorRef?.el) {
            return;
        }
        this.popover.open(this.contextMenuAnchorRef.el, {
            rtcSession: this.rtcSession,
        });
    }
}
