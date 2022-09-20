/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

import fieldUtils from 'web.field_utils';
import { getLangTimeFormat } from 'web.time';

registerModel({
    name: 'calendar.event',
    fields: {
        allday: attr(),
        attendee_status: attr(),
        formattedStart: attr({
            compute() {
                if (!this.start) {
                    return clear();
                }
                return moment(fieldUtils.parse.datetime(this.start, false, { isUTC: true })).local().format(getLangTimeFormat());
            },
        }),
        id: attr({
            identifying: true,
        }),
        name: attr(),
        start: attr(),
    },
});
