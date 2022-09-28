/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { many, one } from '@mail/model/model_field';
import { clear } from '@mail/model/model_field_command';

registerModel({
    name: 'MailTemplateViewOwner',
    identifyingMode: 'xor',
    fields: {
        activity: one('Activity', {
            compute() {
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.activity;
                }
                if (this.activityViewOwner) {
                    return this.activityViewOwner.activity;
                }
                return clear();
            },
        }),
        activityListViewItemOwner: one('ActivityListViewItem', {
            identifying: true,
            inverse: 'mailTemplateViewOwner',
        }),
        activityViewOwner: one('ActivityView', {
            identifying: true,
            inverse: 'mailTemplateViewOwner',
        }),
        mailTemplateViews: many('MailTemplateView', {
            compute() {
                if (!this.activity) {
                    return clear();
                }
                return this.activity.mailTemplates.map(mailTemplate => ({ mailTemplate }));
            },
            inverse: 'owner',
        }),
    },
});
