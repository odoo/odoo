/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { one } from '@mail/model/model_field';

registerModel({
    name: 'MailTemplateView',
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickPreview(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mailTemplate.preview(this.activityViewOwner.activity);
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickSend(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mailTemplate.send(this.activityViewOwner.activity);
        },
    },
    fields: {
        activityViewOwner: one('ActivityView', {
            identifying: true,
            inverse: 'mailTemplateViews',
            readonly: true,
            required: true,
        }),
        mailTemplate: one('MailTemplate', {
            identifying: true,
            readonly: true,
            required: true,
        }),
    },
});
