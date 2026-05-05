/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ListRenderer } from "@web/views/list/list_renderer";

patch(ListRenderer.prototype, {
    setup() {
        super.setup();
        this.widths = JSON.parse(localStorage.getItem("widths") || "{}");
    },

    getColumnWidth(column) {
        if (this.widths[column.name]) {
            return this.widths[column.name];
        }

        if (column.name === "name") {
            console.log("LOADED")
            return 100;
        }

        return column.width || 90;
    },
});