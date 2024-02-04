/** @odoo-module **/

import {ListRenderer} from "@web/views/list/list_renderer";
import {browser} from "@web/core/browser/browser";
import {patch} from "web.utils";

patch(ListRenderer.prototype, "web_remember_tree_column_width.ListRenderer", {
    /**
     * @override
     */
    computeColumnWidthsFromContent() {
        const columnWidths = this._super.apply(this, arguments);
        const table = this.tableRef.el;
        const thElements = [...table.querySelectorAll("thead th")];
        thElements.forEach((el, elIndex) => {
            const fieldName = $(el).data("name");
            if (
                !el.classList.contains("o_list_button") &&
                this.props.list.resModel &&
                fieldName &&
                browser.localStorage
            ) {
                const storedWidth = browser.localStorage.getItem(
                    `odoo.columnWidth.${this.props.list.resModel}.${fieldName}`
                );
                if (storedWidth) {
                    columnWidths[elIndex] = parseInt(storedWidth, 10);
                }
            }
        });
        return columnWidths;
    },

    /**
     * @override
     */
    onStartResize(ev) {
        this._super.apply(this, arguments);
        const resizeStoppingEvents = ["keydown", "mousedown", "mouseup"];
        const $th = $(ev.target.closest("th"));
        if (!$th || !$th.is("th")) {
            return;
        }
        const saveWidth = (saveWidthEv) => {
            if (saveWidthEv.type === "mousedown" && saveWidthEv.which === 1) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            const fieldName = $th.length ? $th.data("name") : undefined;
            if (this.props.list.resModel && fieldName && browser.localStorage) {
                browser.localStorage.setItem(
                    "odoo.columnWidth." + this.props.list.resModel + "." + fieldName,
                    parseInt(($th[0].style.width || "0").replace("px", ""), 10) || 0
                );
            }
            for (const eventType of resizeStoppingEvents) {
                browser.removeEventListener(eventType, saveWidth);
            }
            document.activeElement.blur();
        };
        for (const eventType of resizeStoppingEvents) {
            browser.addEventListener(eventType, saveWidth);
        }
    },
});
