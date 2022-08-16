/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { OnChange } from '@mail/model/model_onchange';

registerModel({
    name: 'RtcPeerConnection',
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
        /**
         * The download is allowed when there are views that display the video stream.
         *
         * @private
         * @returns {boolean}
         */
        _computeAcceptsVideoStream() {
            return Boolean(this.rtcSession.callParticipantCards && this.rtcSession.callParticipantCards.length > 0);
        },
        /**
         * @private
         */
        _onChangeAcceptsVideoStream() {
            const transceiver = this.getTransceiver('video');
            if (!transceiver) {
                return;
            }
            const rtc = this.rtcSession.rtcAsConnectedSession;
            if (this.acceptsVideoStream) {
                transceiver.direction = rtc.videoTrack ? 'sendrecv' : 'recvonly';
            } else {
                transceiver.direction = rtc.videoTrack ? 'sendonly' : 'inactive';
            }
        },
    },
    fields: {
        /**
         * Determines whether the video stream receiver accepts video stream download.
         */
        acceptsVideoStream: attr({
            compute: '_computeAcceptsVideoStream',
        }),
        /**
         * Contains the browser.RTCPeerConnection instance of this RTC Session.
         * If unset, this RTC Session is not considered as connected
         */
        peerConnection: attr(),
        rtcSession: one('RtcSession', {
            identifying: true,
            inverse: 'rtcPeerConnection',
            readonly: true,
            required: true,
        }),
    },
    onChanges: [
        new OnChange({
            dependencies: ['acceptsVideoStream'],
            methodName: '_onChangeAcceptsVideoStream',
        }),
    ],
});
