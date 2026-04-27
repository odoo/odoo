import { Activity } from "@mail/core/web/activity_model";

import { patch } from "@web/core/utils/patch";

patch(Activity.prototype, {
    async markAsDone(attachmentIds = []) {
        await super.markAsDone(...arguments);
        if (this.chaining_type === "trigger") {
            // Refresh as the trigger might have created a new document
            this?.store?.env?.services["document.document"]?.reload();
        }
    },
});
