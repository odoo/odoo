/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MailTemplateView',
    identifyingFields: ['activityViewOwner', 'mailTemplate'],
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickPreview(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mailTemplate.preview(this.activityViewOwner.activity);
        },
    },
    fields: {
        activityViewOwner: one('ActivityView', {
            inverse: 'mailTemplateViews',
            readonly: true,
            required: true,
        }),
        mailTemplate: one('MailTemplate', {
            readonly: true,
            required: true,
        }),
    },
});
