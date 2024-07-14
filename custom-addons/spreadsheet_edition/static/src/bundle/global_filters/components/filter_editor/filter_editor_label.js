/** @odoo-module */

import { Component, onMounted, useRef } from "@odoo/owl";

export class FilterEditorLabel extends Component {
    setup() {
        this.labelInput = useRef("labelInput");
        onMounted(this.onMounted);
    }

    onMounted() {
        this.labelInput.el.focus();
    }
}
FilterEditorLabel.template = "spreadsheet_edition.FilterEditorLabel";

FilterEditorLabel.props = {
    label: { type: String, optional: true },
    placeholder: { type: String, optional: true },
    inputClass: { type: String, optional: true },
    setLabel: Function,
};
