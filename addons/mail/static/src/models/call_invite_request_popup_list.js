/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'CallInviteRequestPopupList',
    fields: {
        callSystrayMenuOwner: one('CallSystrayMenu', {
            identifying: true,
            inverse: 'callInviteRequestPopupList',
        }),
    },
});
