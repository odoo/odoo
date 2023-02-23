/** @odoo-module **/

import { attr, clear, one, Model } from "@mail/model";

Model({
    name: "ListFieldActivityView",
    template: "mail.ListFieldActivityView",
    fields: {
        activityButtonView: one("ActivityButtonView", {
            default: {},
            inverse: "listFieldActivityViewOwner",
            required: true,
        }),
        id: attr({ identifying: true }),
        summaryText: attr({
            default: "",
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
        }),
        thread: one("Thread", { required: true }),
        webRecord: attr({ required: true }),
    },
});
