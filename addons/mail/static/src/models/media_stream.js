/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';

registerModel({
    name: 'MediaStream',
    lifecycleHooks: {
        _willDelete() {
            for (const track of this.webMediaStream.getTracks()) {
                track.stop();
            }
        },
    },
    fields: {
        id: attr({
            identifying: true,
        }),
        webMediaStream: attr({
            required: true,
            readonly: true,
        }),
    },
});
