/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear, insertAndReplace, replace } from '@mail/model/model_field_command';
import { isEventHandled, markEventHandled } from '@mail/utils/utils';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'CallParticipantCard',
    identifyingFields: [['rtcSession', 'invitedMember'], ['callViewAsMainCard', 'callViewAsTile']],
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
            if (this.rtcSession) {
                if (this.callView.activeRtcSession === this.rtcSession && this.callViewAsMainCard) {
                    this.callView.update({ activeRtcSession: clear() });
                } else {
                    this.callView.update({ activeRtcSession: replace(this.rtcSession) });
                }
                return;
            }
            const channel = this.channel;
            const channelData = await this.messaging.rpc(({
                route: '/mail/rtc/channel/cancel_call_invitation',
                params: {
                    channel_id: this.channel.id,
                    member_ids: this.invitedMember && [this.invitedMember.id],
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
            if (this.invitedMember) {
                return this.invitedMember.avatarUrl;
            }
        },
        /**
         * @private
         * @returns {mail.callView}
         */
        _computeCallView() {
            const callView = this.callViewAsMainCard || this.callViewAsTile;
            if (callView) {
                return replace(callView);
            } else {
                return clear();
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
         * @returns {string}
         */
        _computeName() {
            if (this.rtcSession) {
                return this.rtcSession.name;
            }
            if (this.invitedMember) {
                return this.invitedMember.name;
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
        invitedMember: one('ChannelMember', {
            readonly: true,
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
         * The callView that displays this card.
         */
        callView: one('CallView', {
            compute: '_computeCallView',
            inverse: 'participantCards',
        }),
        /**
         * The call view for which this card is the main card.
         */
        callViewAsMainCard: one('CallView', {
            inverse: 'mainParticipantCard',
            readonly: true,
        }),
        /**
         * The call view for which this card is one of the tiles.
         */
        callViewAsTile: one('CallView', {
            inverse: 'tileParticipantCards',
            readonly: true,
        }),
        /**
         * If set, this card represents a rtcSession.
         */
        rtcSession: one('RtcSession', {
            inverse: 'callParticipantCards',
            readonly: true,
        }),
        callParticipantVideoView: one('CallParticipantVideoView', {
            compute: '_computeCallParticipantVideoView',
            inverse: 'callParticipantCardOwner',
            isCausal: true,
        }),
        volumeMenuAnchorRef: attr(),
    },
});
