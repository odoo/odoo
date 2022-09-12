/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'CallParticipantCardPopoverContentView',
    recordMethods: {
        /**
         * @param {Event} ev
         */
        onChangeVolume(ev) {
            this.callParticipantCardView.rtcSession && this.callParticipantCardView.rtcSession.setVolume(parseFloat(ev.target.value));
        },
    },
    fields: {
        callParticipantCardView: one('CallParticipantCardView', {
            related: 'popoverViewOwner.callParticipantCardViewOwner',
        }),
        /**
         * Determines whether or not we show the connection info.
         */
        hasConnectionInfo: attr({
            compute() {
                return Boolean(this.callParticipantCardView.rtcSession && this.env.debug && this.callParticipantCardView.channelMember.channel.thread.rtc);
            },
        }),
        /**
         * The text describing the inbound ice connection candidate type.
         */
        inboundConnectionTypeText: attr({
            compute() {
                if (!this.callParticipantCardView.rtcSession || !this.callParticipantCardView.rtcSession.remoteCandidateType) {
                    return sprintf(this.env._t('From %s: no connection'), this.callParticipantCardView.channelMember.persona.name);
                }
                return sprintf(
                    this.env._t('From %(name)s: %(candidateType)s (%(protocol)s)'), {
                        candidateType: this.callParticipantCardView.rtcSession.remoteCandidateType,
                        name: this.callParticipantCardView.channelMember.persona.name,
                        protocol: this.messaging.rtc.protocolsByCandidateTypes[this.callParticipantCardView.rtcSession.remoteCandidateType],
                    },
                );
            },
        }),
        /**
         * The text describing the outbound ice connection candidate type.
         */
        outboundConnectionTypeText: attr({
            compute() {
                if (!this.callParticipantCardView.rtcSession || !this.callParticipantCardView.rtcSession.localCandidateType) {
                    return sprintf(this.env._t('To %s: no connection'), this.callParticipantCardView.channelMember.persona.name);
                }
                return sprintf(
                    this.env._t('To %(name)s: %(candidateType)s (%(protocol)s)'), {
                        candidateType: this.callParticipantCardView.rtcSession.localCandidateType,
                        name: this.callParticipantCardView.channelMember.persona.name,
                        protocol: this.messaging.rtc.protocolsByCandidateTypes[this.callParticipantCardView.rtcSession.localCandidateType],
                    },
                );
            },
        }),
        popoverViewOwner: one('PopoverView', {
            identifying: true,
            inverse: 'callParticipantCardPopoverContentView',
        })
    },
});
