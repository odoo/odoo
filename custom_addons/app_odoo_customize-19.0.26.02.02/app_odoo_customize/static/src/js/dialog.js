/** @odoo-module **/

import { Dialog } from "@web/core/dialog/dialog";
import { patch } from "@web/core/utils/patch";
import { session } from "@web/session";

patch(Dialog.prototype, {
    setup() {
        super.setup();
        const app_system_name = session.app_system_name || "odooApp";
        this.title = app_system_name;
    },
    
});

