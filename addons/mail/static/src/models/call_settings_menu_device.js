/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

registerModel({
    name: 'CallSettingsMenuDevice',
    fields: {
        callSettingsMenuOwner: one('CallSettingsMenu', {
            identifying: true,
            inverse: 'devices',
        }),
        webMediaDevice: attr({
            identifying: true,
        }),
    },
});
