/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'RtcDataChannel',
    identifyingFields: ['rtcPeerConnectionAsNotificationDataChannel'],
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
        rtcPeerConnectionAsNotificationDataChannel: one('RtcPeerConnection', {
            inverse: 'notificationDataChannel',
            readonly: true,
            required: true,
        }),
    },
});
