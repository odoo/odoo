/** @odoo-module **/

import { attr, one, registerModel } from '@mail/model';

registerModel({
    name: 'RtcDataChannel',
    lifecycleHooks: {
        _willDelete() {
            this.dataChannel.close();
        },
    },
    fields: {
        dataChannel: attr({ required: true, readonly: true }),
        rtcSession: one('RtcSession', { identifying: true, inverse: 'rtcDataChannel' }),
    },
});
