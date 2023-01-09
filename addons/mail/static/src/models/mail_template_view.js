/** @odoo-module **/

import { one, Model } from "@mail/model";

Model({
    name: "MailTemplateView",
    template: "mail.MailTemplateView",
    recordMethods: {
        /**
         * @param {MouseEvent} ev
         */
        onClickPreview(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mailTemplate.preview(this.activity);
            if (this.activityListViewItemOwner) {
                this.activityListViewItemOwner.activityListViewOwner.popoverViewOwner.delete();
            }
        },
        /**
         * @param {MouseEvent} ev
         */
        onClickSend(ev) {
            ev.stopPropagation();
            ev.preventDefault();
            this.mailTemplate.send(this.activity);
            if (this.activityListViewItemOwner) {
                this.activityListViewItemOwner.activityListViewOwner.popoverViewOwner.delete();
            }
        },
    },
    fields: {
        activity: one("Activity", {
            compute() {
                if (this.activityViewOwner) {
                    return this.activityViewOwner.activity;
                }
                if (this.activityListViewItemOwner) {
                    return this.activityListViewItemOwner.activity;
                }
            },
        }),
        activityListViewItemOwner: one("ActivityListViewItem", { inverse: "mailTemplateViews" }),
        activityViewOwner: one("ActivityView", { inverse: "mailTemplateViews" }),
        mailTemplate: one("MailTemplate", { identifying: true }),
    },
});
