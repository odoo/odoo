/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'RtcDataChannel',
    identifyingFields: ['rtcSession'],
    lifecycleHooks: {
        _willDelete() {
            this.dataChannel.close();
        },
    },
    fields: {
        dataChannel: attr({
            required: true,
            readonly: true,
        }),
        rtcSession: one('RtcSession', {
            inverse: 'rtcDataChannel',
            readonly: true,
            required: true,
        }),
    },
});
