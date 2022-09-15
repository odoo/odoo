/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import { sprintf } from '@web/core/utils/strings';

registerModel({
    name: 'CallSystrayMenu',
    fields: {
        buttonTitle: attr({
            compute() {
                if (!this.messaging.rtc.channel) {
                    return clear();
                }
                return sprintf(
                    this.env._t("Open conference: %s"),
                    this.messaging.rtc.channel.displayName,
                );
            },
            default: '',
        }),
        rtc: one('Rtc', {
            identifying: true,
            inverse: 'callSystrayMenu',
        }),
    },
});
