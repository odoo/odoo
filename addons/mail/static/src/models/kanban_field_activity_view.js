/** @odoo-module **/

import { attr, one, Model } from "@mail/model";

Model({
    name: "KanbanFieldActivityView",
    template: "mail.KanbanFieldActivityView",
    fields: {
        activityButtonView: one("ActivityButtonView", {
            default: {},
            inverse: "kanbanFieldActivityViewOwner",
            required: true,
        }),
        id: attr({ identifying: true }),
        thread: one("Thread", { required: true }),
        webRecord: attr({ required: true }),
    },
});
