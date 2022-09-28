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
            this.mailTemplate.preview(this.owner.activity);
            if (this.owner.activityListViewOwner) {
                this.owner.activityListViewOwner.popoverViewOwner.delete();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickSend(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mailTemplate.send(this.owner.activity);
        },
    },
    fields: {
        mailTemplate: one('MailTemplate', {
            identifying: true,
        }),
        owner: one('MailTemplateViewOwner', {
            identifying: true,
            inverse: 'mailTemplateViews',
        }),
    },
});
