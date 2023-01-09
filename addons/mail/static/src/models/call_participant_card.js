/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";
import { isEventHandled, markEventHandled } from "@mail/utils/utils";

Model({
    name: "CallParticipantCard",
    template: "mail.CallParticipantCard",
    identifyingMode: "xor",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onClick(ev) {
            if (isEventHandled(ev, "CallParticipantCard.clickVolumeAnchor")) {
                return;
            }
            if (this.rtcSession) {
                if (this.callView.activeRtcSession === this.rtcSession && this.mainViewTileOwner) {
                    this.callView.channel.update({ activeRtcSession: clear() });
                } else {
                    this.callView.channel.update({ activeRtcSession: this.rtcSession });
                }
                return;
            }
            const channel = this.channelMember.channel.thread;
            const channelData = await this.messaging.rpc({
                route: "/mail/rtc/channel/cancel_call_invitation",
                params: {
                    channel_id: channel.id,
                    member_ids: [this.channelMember.id],
                },
            });
            if (!channel.exists()) {
                return;
            }
            channel.update(channelData);
        },
        /**
         * Handled by the popover component.
         *
         * @param {MouseEvent} ev
         */
        async onClickVolumeAnchor(ev) {
            markEventHandled(ev, "CallParticipantCard.clickVolumeAnchor");
            this.update({
                callParticipantCardPopoverView: this.callParticipantCardPopoverView ? clear() : {},
            });
        },
        /**
         * This listens to the right click event, and used to redirect the event
         * as a click on the popover.
         *
         * @param {Event} ev
         */
        async onContextMenu(ev) {
            ev.preventDefault();
            if (!this.volumeMenuAnchorRef || !this.volumeMenuAnchorRef.el) {
                return;
            }
            this.volumeMenuAnchorRef.el.click();
        },
    },
    fields: {
        callParticipantCardPopoverView: one("PopoverView", { inverse: "callParticipantCardOwner" }),
        channelMember: one("ChannelMember", {
            inverse: "callParticipantCards",
            compute() {
                if (this.sidebarViewTileOwner) {
                    return this.sidebarViewTileOwner.channelMember;
                }
                return this.mainViewTileOwner.channelMember;
            },
        }),
        mainViewTileOwner: one("CallMainViewTile", {
            identifying: true,
            inverse: "participantCard",
        }),
        /**
         * Determines if this card has to be displayed in a minimized form.
         */
        isMinimized: attr({
            default: false,
            compute() {
                return Boolean(this.callView && this.callView.isMinimized);
            },
        }),
        /**
         * Determines if the rtcSession is in a valid "talking" state.
         */
        isTalking: attr({
            default: false,
            compute() {
                return Boolean(
                    this.rtcSession && this.rtcSession.isTalking && !this.rtcSession.isMute
                );
            },
        }),
        /**
         * The callView that displays this card.
         */
        callView: one("CallView", {
            inverse: "participantCards",
            compute() {
                if (this.sidebarViewTileOwner) {
                    return this.sidebarViewTileOwner.callSidebarViewOwner.callView;
                }
                return this.mainViewTileOwner.callMainViewOwner.callView;
            },
        }),
        rtcSession: one("RtcSession", {
            inverse: "callParticipantCards",
            related: "channelMember.rtcSession",
        }),
        sidebarViewTileOwner: one("CallSidebarViewTile", {
            identifying: true,
            inverse: "participantCard",
        }),
        callParticipantVideoView: one("CallParticipantVideoView", {
            inverse: "callParticipantCardOwner",
            compute() {
                if (this.rtcSession && this.rtcSession.videoStream) {
                    return {};
                }
                return clear();
            },
        }),
        volumeMenuAnchorRef: attr({ ref: "volumeMenuAnchor" }),
    },
});
