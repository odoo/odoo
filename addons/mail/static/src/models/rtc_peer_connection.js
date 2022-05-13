/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'RtcPeerConnection',
    identifyingFields: ['rtcSession'],
    lifecycleHooks: {
        _willDelete() {
            this.peerConnection.close();
        }
    },
    recordMethods: {
        /**
         * @param {String} trackKind
         * @returns {RTCRtpTransceiver} the transceiver used for this trackKind.
         */
        getTransceiver(trackKind) {
            const transceivers = this.peerConnection.getTransceivers();
            return transceivers[this.messaging.rtc.orderedTransceiverNames.indexOf(trackKind)];
        },
    },
    fields: {
        /**
         * Contains the browser.RTCPeerConnection instance of this RTC Session.
         * If unset, this RTC Session is not considered as connected
         */
        peerConnection: attr(),
        rtcSession: one('RtcSession', {
            inverse: 'rtcPeerConnection',
            readonly: true,
            required: true,
        }),
    },
});
