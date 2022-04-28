/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'RtcVideoView',
    identifyingFields: ['rtcCallParticipantCardOwner'],
    fields: {
        rtcCallParticipantCardOwner: one('RtcCallParticipantCard', {
            inverse: 'rtcVideoView',
            readonly: true,
            required: true,
        }),
    },
});
