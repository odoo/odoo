/** @odoo-module **/

import { WebClient } from "@web/webclient/webclient";
import { patch } from "web.utils";

patch(WebClient.prototype, "customize_title_header.WebClient", {
    setup() {
        this._super();
        this.title.setParts({ zopenerp: "Innoway" });
    },
});