/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "web.utils";

patch(WebClient.prototype, "bdtask_custom_title_and_favicon.WebClient", {
    setup() {
        this._super();
        this.title.setParts({ zopenerp: "Custom" });
    },
});