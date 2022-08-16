/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallParticipantVideoView',
    recordMethods: {
        /**
         * Plays the video as some browsers may not support or block autoplay.
         *
         * @param {Event} ev
         */
        async onVideoLoadedMetaData(ev) {
            try {
                await ev.target.play();
            } catch (error) {
                if (typeof error === 'object' && error.name === 'NotAllowedError') {
                    // Ignored as some browsers may reject play() calls that do not
                    // originate from a user input.
                    return;
                }
                throw error;
            }
        },
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeRtcSession() {
            if (this.callParticipantCardOwner.rtcSession) {
                return replace(this.callParticipantCardOwner.rtcSession);
            }
            return clear();
        },
    },
    fields: {
        callParticipantCardOwner: one('CallParticipantCard', {
            identifying: true,
            inverse: 'callParticipantVideoView',
            readonly: true,
            required: true,
        }),
        rtcSession: one('RtcSession', {
            compute: '_computeRtcSession',
            readonly: true,
        }),
    },
});
