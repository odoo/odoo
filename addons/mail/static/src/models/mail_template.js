/** @odoo-module **/

import { attr, many, Model } from "@mail/model";

Model({
    name: "MailTemplate",
    recordMethods: {
        /**
         * @param {Activity} activity
         */
        preview(activity) {
            const action = {
                name: this.env._t("Compose Email"),
                type: "ir.actions.act_window",
                res_model: "mail.compose.message",
                views: [[false, "form"]],
                target: "new",
                context: {
                    default_res_ids: [activity.thread.id],
                    default_model: activity.thread.model,
                    default_subtype_xmlid: 'mail.mt_comment',
                    default_template_id: this.id,
                    force_email: true,
                },
            };
            this.env.services.action.doAction(action, {
                onClose: () => activity.thread.fetchData(["attachments", "messages"]),
            });
        },
        /**
         * @param {Activity} activity
         */
        async send(activity) {
            const thread = activity.thread;
            await this.messaging.rpc({
                model: activity.thread.model,
                method: "activity_send_mail",
                args: [[activity.thread.id], this.id],
            });
            if (thread.exists()) {
                thread.fetchData(["attachments", "messages"]);
            }
        },
    },
    fields: {
        activities: many("Activity", { inverse: "mailTemplates" }),
        id: attr({ identifying: true }),
        name: attr(),
    },
});
