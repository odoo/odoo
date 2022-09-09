/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'ListFieldActivityView',
    fields: {
        activityButtonView: one('ActivityButtonView', {
            default: {},
            inverse: 'listFieldActivityViewOwner',
            required: true,
        }),
        id: attr({
            identifying: true,
        }),
        summaryText: attr({
            compute() {
                if (this.thread.activities.length === 0) {
                    return clear();
                }
                if (this.webRecord.data.activity_exception_decoration) {
                    return this.env._t("Warning");
                }
                if (this.webRecord.data.activity_summary) {
                    return this.webRecord.data.activity_summary;
                }
                if (this.webRecord.data.activity_type_id) {
                    return this.webRecord.data.activity_type_id[1]; // 1 = display_name
                }
                return clear();
            },
            default: '',
        }),
        thread: one('Thread', {
            required: true,
        }),
        webRecord: attr({
            required: true,
        }),
    },
});
