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
            this.callParticipantCard.rtcSession && this.callParticipantCard.rtcSession.setVolume(parseFloat(ev.target.value));
        },
    },
    fields: {
        callParticipantCard: one('CallParticipantCard', {
            related: 'popoverViewOwner.callParticipantCardOwner',
        }),
        /**
         * Determines whether or not we show the connection info.
         */
        hasConnectionInfo: attr({
            compute() {
                return Boolean(this.callParticipantCard.rtcSession && this.env.debug && this.callParticipantCard.channelMember.channel.thread.rtc);
            },
        }),
        /**
         * The text describing the inbound ice connection candidate type.
         */
        inboundConnectionTypeText: attr({
            compute() {
                if (!this.callParticipantCard.rtcSession || !this.callParticipantCard.rtcSession.remoteCandidateType) {
                    return sprintf(this.env._t('From %s: no connection'), this.callParticipantCard.channelMember.persona.name);
                }
                return sprintf(
                    this.env._t('From %(name)s: %(candidateType)s (%(protocol)s)'), {
                        candidateType: this.callParticipantCard.rtcSession.remoteCandidateType,
                        name: this.callParticipantCard.channelMember.persona.name,
                        protocol: this.messaging.rtc.protocolsByCandidateTypes[this.callParticipantCard.rtcSession.remoteCandidateType],
                    },
                );
            },
        }),
        /**
         * The text describing the outbound ice connection candidate type.
         */
        outboundConnectionTypeText: attr({
            compute() {
                if (!this.callParticipantCard.rtcSession || !this.callParticipantCard.rtcSession.localCandidateType) {
                    return sprintf(this.env._t('To %s: no connection'), this.callParticipantCard.channelMember.persona.name);
                }
                return sprintf(
                    this.env._t('To %(name)s: %(candidateType)s (%(protocol)s)'), {
                        candidateType: this.callParticipantCard.rtcSession.localCandidateType,
                        name: this.callParticipantCard.channelMember.persona.name,
                        protocol: this.messaging.rtc.protocolsByCandidateTypes[this.callParticipantCard.rtcSession.localCandidateType],
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
