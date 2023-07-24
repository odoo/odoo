/* @odoo-module */

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, "mail/views/web", {
    onWillLoadRoot() {
        if (this.model.root) {
            // not first load
            const { resModel, resId } = this.model.root;
            this.env.bus.trigger("MAIL:RELOAD-THREAD", { resModel, resId });
        }
    },
});
