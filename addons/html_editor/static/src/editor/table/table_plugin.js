/** @odoo-module */

import { parseHTML } from "../core/utils";
import { Plugin } from "../plugin";
import { TablePicker } from "./table_picker";

export class TablePlugin extends Plugin {
    static name = "table";
    static dependencies = ["history", "overlay"];

    constructor() {
        super(...arguments);
        /** @type {import("../core/overlay_plugin").Overlay} */
        this.picker = this.shared.createOverlay(TablePicker, "bottom", {
            dispatch: this.dispatch,
            el: this.el,
        });
    }

    handleCommand(command, payload) {
        switch (command) {
            case "OPEN_TABLE_PICKER":
                this.openPicker();
                break;
            case "INSERT_TABLE":
                this.insertTable(payload.cols, payload.rows);
                break;
        }
    }

    openPicker() {
        const range = getSelection().getRangeAt(0);
        const rect = range.getBoundingClientRect();
        if (rect.width === 0 && rect.height === 0 && rect.x === 0) {
            this.shared.disableObserver();
            range.startContainer.parentElement.appendChild(document.createElement("br"));
            this.shared.enableObserver();
        }
        this.picker.open();
    }

    insertTable(colNumber, rowNumber) {
        const tdsHtml = new Array(colNumber).fill("<td><p><br></p></td>").join("");
        const trsHtml = new Array(rowNumber).fill(`<tr>${tdsHtml}</tr>`).join("");
        const tableHtml = `<table class="table table-bordered o_table"><tbody>${trsHtml}</tbody></table>`;
        const sel = getSelection();
        const elem = sel.anchorNode.parentElement;
        const tableElem = parseHTML(document, tableHtml);
        elem.appendChild(tableElem);
    }
}
