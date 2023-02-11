/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one, one2one } from '@mail/model/model_field';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

function factory(dependencies) {

    class RtcCallParticipantCard extends dependencies['mail.model'] {

        /**
         * @override
         */
        _created() {
            super._created();
            this.onChangeVolume = this.onChangeVolume.bind(this);
            this.onClick = this.onClick.bind(this);
            this.onClickVolumeAnchor = this.onClickVolumeAnchor.bind(this);
        }

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------

        /**
         * @param {Event} ev
         */
        onChangeVolume(ev) {
            this.rtcSession && this.rtcSession.setVolume(parseFloat(ev.target.value));
        }

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
            const channelData = await this.env.services.rpc(({
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
        }

        /**
         * Handled by the popover component.
         *
         * @param {MouseEvent} ev
         */
        async onClickVolumeAnchor(ev) {
            markEventHandled(ev, 'CallParticipantCard.clickVolumeAnchor');
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

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
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsMinimized() {
            const callViewer = this.rtcCallViewerOfMainCard || this.rtcCallViewerOfTile;
            return Boolean(callViewer && callViewer.isMinimized);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsInvitation() {
            return Boolean(this.invitedPartner || this.invitedGuest);
        }

        /**
         * @private
         * @returns {boolean}
         */
        _computeIsTalking() {
            return Boolean(this.rtcSession && this.rtcSession.isTalking && !this.rtcSession.isMuted);
        }

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
        }

    }

    RtcCallParticipantCard.fields = {
        /**
         * The relative url of the image that represents the card.
         */
        avatarUrl: attr({
            compute: '_computeAvatarUrl',
        }),
        /**
         * The channel of the call.
         */
        channel: many2one('mail.thread', {
            required: true,
        }),
        /**
         * If set, this card represents an invitation of this guest to this call.
         */
        invitedGuest: many2one('mail.guest'),
        /**
         * If set, this card represents an invitation of this partner to this call.
         */
        invitedPartner: many2one('mail.partner'),
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
         * Unique id for this session provided when instantiated.
         */
        relationalId: attr({
            readonly: true,
            required: true,
        }),
        /**
         * The callViewer for which this card is the spotlight.
         */
        rtcCallViewerOfMainCard: one2one('mail.rtc_call_viewer', {
            inverse: 'mainParticipantCard',
        }),
        /**
         * The callViewer for which this card is one of the tiles.
         */
        rtcCallViewerOfTile: many2one('mail.rtc_call_viewer', {
            inverse: 'tileParticipantCards',
        }),
        /**
         * If set, this card represents a rtcSession.
         */
        rtcSession: many2one('mail.rtc_session'),
    };
    RtcCallParticipantCard.identifyingFields = ['relationalId'];
    RtcCallParticipantCard.modelName = 'mail.rtc_call_participant_card';

    return RtcCallParticipantCard;
}

registerNewModel('mail.rtc_call_participant_card', factory);
