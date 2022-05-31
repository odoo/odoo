/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';
import { clear, replace } from '@mail/model/model_field_command';

registerModel({
    name: 'CallParticipantVideoView',
    identifyingFields: ['callParticipantCardOwner'],
    recordMethods: {
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
