/** @odoo-module */

import { Component, onMounted, useRef } from "@odoo/owl";

export class FilterEditorLabel extends Component {
    static template = "spreadsheet_edition.FilterEditorLabel";
    static props = {
        label: { type: String, optional: true },
        placeholder: { type: String, optional: true },
        inputClass: { type: String, optional: true },
        setLabel: Function,
    };

    setup() {
        this.labelInput = useRef("labelInput");
        onMounted(this.onMounted);
    }

    onMounted() {
        this.labelInput.el.focus();
    }
}
