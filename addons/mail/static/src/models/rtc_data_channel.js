/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'RtcDataChannel',
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
            identifying: true,
            inverse: 'rtcDataChannel',
            readonly: true,
            required: true,
        }),
    },
});
