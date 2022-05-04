/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'RtcActivityNoticeView',
    identifyingFields: ['rtc'],
    fields: {
        rtc: one('Rtc', {
            inverse: 'rtcActivityNoticeView',
            readonly: true,
            required: true,
        }),
    },
});
