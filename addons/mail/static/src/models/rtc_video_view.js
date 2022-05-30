/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallParticipantVideoView',
    identifyingFields: ['rtcCallParticipantCardOwner'],
    recordMethods: {
        /**
         * @private
         * @returns {FieldCommand}
         */
        _computeRtcSession() {
            if (this.rtcCallParticipantCardOwner.rtcSession) {
                return replace(this.rtcCallParticipantCardOwner.rtcSession);
            }
            return clear();
        },
    },
    fields: {
        rtcCallParticipantCardOwner: one('RtcCallParticipantCard', {
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
