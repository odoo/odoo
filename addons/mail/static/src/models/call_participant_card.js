/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

registerModel({
    name: 'CallParticipantCard',
    identifyingMode: 'xor',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        async onClick(ev) {
            if (isEventHandled(ev, 'CallParticipantCard.clickVolumeAnchor')) {
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
            const channelData = await this.messaging.rpc(({
                route: '/mail/rtc/channel/cancel_call_invitation',
                params: {
                    channel_id: channel.id,
                    member_ids: [this.channelMember.id],
                },
            }));
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
            markEventHandled(ev, 'CallParticipantCard.clickVolumeAnchor');
            this.update({ callParticipantCardPopoverView: this.callParticipantCardPopoverView ? clear() : {} });
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
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCallView() {
            if (this.sidebarViewTileOwner) {
                return this.sidebarViewTileOwner.callSidebarViewOwner.callView;
            }
            return this.mainViewTileOwner.callMainViewOwner.callView;
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
         _computeChannelMember() {
            if (this.sidebarViewTileOwner) {
                return this.sidebarViewTileOwner.channelMember;
            }
            return this.mainViewTileOwner.channelMember;
         },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsMinimized() {
            return Boolean(this.callView && this.callView.isMinimized);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsTalking() {
            return Boolean(this.rtcSession && this.rtcSession.isTalking && !this.rtcSession.isMute);
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCallParticipantVideoView() {
            if (this.rtcSession && this.rtcSession.videoStream) {
                return {};
            }
            return clear();
        },
    },
    fields: {
        callParticipantCardPopoverView: one('PopoverView', {
            inverse: 'callParticipantCardOwner',
            isCausal: true,
        }),
        channelMember: one('ChannelMember', {
            compute: '_computeChannelMember',
            inverse: 'callParticipantCards',
        }),
        mainViewTileOwner: one('CallMainViewTile', {
            identifying: true,
            inverse: 'participantCard',
        }),
        /**
         * Determines if this card has to be displayed in a minimized form.
         */
        isMinimized: attr({
            default: false,
            compute: '_computeIsMinimized',
        }),
        /**
         * Determines if the rtcSession is in a valid "talking" state.
         */
        isTalking: attr({
            default: false,
            compute: '_computeIsTalking',
        }),
        /**
         * The callView that displays this card.
         */
        callView: one('CallView', {
            compute: '_computeCallView',
            inverse: 'participantCards',
        }),
        rtcSession: one('RtcSession', {
            related: 'channelMember.rtcSession',
            inverse: 'callParticipantCards',
        }),
        sidebarViewTileOwner: one('CallSidebarViewTile', {
            identifying: true,
            inverse: 'participantCard',
        }),
        callParticipantVideoView: one('CallParticipantVideoView', {
            compute: '_computeCallParticipantVideoView',
            inverse: 'callParticipantCardOwner',
            isCausal: true,
        }),
        volumeMenuAnchorRef: attr(),
    },
});
