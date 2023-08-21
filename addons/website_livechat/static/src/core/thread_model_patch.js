/** @odoo-module */

import { Thread } from "@mail/core/common/thread_model";
import { patch } from "@web/core/utils/patch";

patch(Thread, {
    update(thread, data) {
        super.update(thread, data);
        if (data?.visitor) {
            thread.visitor = this.store.Persona.insert({
                ...data.visitor,
                type: "visitor",
            });
        }
    },
});
