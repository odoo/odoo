/** @odoo-module */
import { ListRenderer } from "@web/views/list/list_renderer";
import { patch } from "@web/core/utils/patch";


patch(ListRenderer.prototype, {
    onGlobalClick(ev) {
        if (!this.props.list.editedRecord) {
            return; // there's no row in edition
        }

        this.tableRef.el.querySelector("tbody").classList.remove("o_keyboard_navigation");

        const target = ev.target;
        if (this.tableRef.el.contains(target) && target.closest(".o_data_row")) {
            // ignore clicks inside the table that are originating from a record row
            // as they are handled directly by the renderer.
            return;
        }
        if (this.activeElement !== this.uiService.activeElement) {
            return;
        }
        // DateTime picker
        if (target.closest(".o_datetime_picker")) {
            return;
        }
        // Legacy autocomplete
        if (ev.target.closest(".ui-autocomplete")) {
            return;
        }
    }

})
