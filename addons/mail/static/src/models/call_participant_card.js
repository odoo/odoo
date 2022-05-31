/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'CallParticipantCard',
    identifyingFields: ['relationalId'],
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onChangeVolume(ev) {
            this.rtcSession && this.rtcSession.setVolume(parseFloat(ev.target.value));
        },
        /**
         * @param {MouseEvent} ev
         */
        async onClick(ev) {
            if (isEventHandled(ev, 'CallParticipantCard.clickVolumeAnchor')) {
                return;
            }
            if (!this.invitedPartner && !this.invitedGuest) {
                if (!this.isMinimized) {
                    this.messaging.toggleFocusedRtcSession(this.rtcSession.id);
                }
                return;
            }
            const channel = this.channel;
            const channelData = await this.messaging.rpc(({
                route: '/mail/rtc/channel/cancel_call_invitation',
                params: {
                    channel_id: this.channel.id,
                    partner_ids: this.invitedPartner && [this.invitedPartner.id],
                    guest_ids: this.invitedGuest && [this.invitedGuest.id],
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
         * @returns {string}
         */
        _computeAvatarUrl() {
            if (!this.channel) {
                return;
            }
            if (this.rtcSession) {
                return this.rtcSession.avatarUrl;
            }
            if (this.invitedPartner) {
                return `/mail/channel/${this.channel.id}/partner/${this.invitedPartner.id}/avatar_128`;
            }
            if (this.invitedGuest) {
                return `/mail/channel/${this.channel.id}/guest/${this.invitedGuest.id}/avatar_128?unique=${this.invitedGuest.name}`;
            }
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeHasConnectionInfo() {
            return Boolean(this.rtcSession && this.env.debug && this.channel.rtc);
        },
        /**
         * @private
         * @returns {string}
         */
        _computeInboundConnectionTypeText() {
            if (!this.rtcSession || !this.rtcSession.remoteCandidateType) {
                return sprintf(this.env._t('From %s: no connection'), this.name);
            }
            return sprintf(
                this.env._t('From %(name)s: %(candidateType)s (%(protocol)s)'), {
                    candidateType: this.rtcSession.remoteCandidateType,
                    name: this.name,
                    protocol: this.messaging.rtc.protocolsByCandidateTypes[this.rtcSession.remoteCandidateType],
                },
            );
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsMinimized() {
            const callView = this.callViewOfMainCard || this.callViewOfTile;
            return Boolean(callView && callView.isMinimized);
        },
        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInvitation() {
            return Boolean(this.invitedPartner || this.invitedGuest);
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
         * @returns {string}
         */
        _computeName() {
            if (this.rtcSession) {
                return this.rtcSession.name;
            }
            if (this.invitedPartner) {
                return this.invitedPartner.name;
            }
            if (this.invitedGuest) {
                return this.invitedGuest.name;
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeOutboundConnectionTypeText() {
            if (!this.rtcSession || !this.rtcSession.localCandidateType) {
                return sprintf(this.env._t('To %s: no connection'), this.name);
            }
            return sprintf(
                this.env._t('To %(name)s: %(candidateType)s (%(protocol)s)'), {
                    candidateType: this.rtcSession.localCandidateType,
                    name: this.name,
                    protocol: this.messaging.rtc.protocolsByCandidateTypes[this.rtcSession.localCandidateType],
                },
            );
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeCallParticipantVideoView() {
            if (this.rtcSession && this.rtcSession.videoStream) {
                return insertAndReplace();
            }
            return clear();
        },
    },
    fields: {
        /**
         * The relative url of the image that represents the card.
         */
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        /**
         * The channel of the call.
         */
        channel: one('Thread', {
            required: true,
        }),
        /**
         * Determines whether or not we show the connection info.
         */
        hasConnectionInfo: attr({
            compute: '_computeHasConnectionInfo',
        }),
        /**
         * The text describing the inbound ice connection candidate type.
         */
        inboundConnectionTypeText: attr({
            compute: '_computeInboundConnectionTypeText',
        }),
        /**
         * If set, this card represents an invitation of this guest to this call.
         */
        invitedGuest: one('Guest'),
        /**
         * If set, this card represents an invitation of this partner to this call.
         */
        invitedPartner: one('Partner'),
        /**
         * States whether this card is representing a person with a pending
         * invitation.
         */
        isInvitation: attr({
            compute: '_computeIsInvitation'
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
         * The name of the rtcSession or the invited partner.
         */
        name: attr({
            default: 'Anonymous',
            compute: '_computeName',
        }),
        /**
         * The text describing the outbound ice connection candidate type.
         */
        outboundConnectionTypeText: attr({
            compute: '_computeOutboundConnectionTypeText',
        }),
        /**
         * Unique id for this session provided when instantiated.
         */
        relationalId: attr({
            readonly: true,
            required: true,
        }),
        /**
         * The call view for which this card is the spotlight.
         */
        callViewOfMainCard: one('CallView', {
            inverse: 'mainParticipantCard',
        }),
        /**
         * The call view for which this card is one of the tiles.
         */
        callViewOfTile: one('CallView', {
            inverse: 'tileParticipantCards',
        }),
        /**
         * If set, this card represents a rtcSession.
         */
        rtcSession: one('RtcSession'),
        callParticipantVideoView: one('CallParticipantVideoView', {
            compute: '_computeCallParticipantVideoView',
            inverse: 'callParticipantCardOwner',
            isCausal: true,
        }),
        volumeMenuAnchorRef: attr(),
    },
});
