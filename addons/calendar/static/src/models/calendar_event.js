/** @odoo-module **/

import { attr, clear, Model } from '@mail/model';

import fieldUtils from 'web.field_utils';
import { getLangTimeFormat } from 'web.time';

Model({
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
