/* @odoo-module **/

import { CheckBox } from "@web/core/checkbox/checkbox";

// We need the actual event when clicking on a checkbox (to support multi select), only accept onClick
export class DocumentsListRendererCheckBox extends CheckBox {
    /**
     * @override
     */
    onChange(ev) {}

    /**
     * @override
     */
    onClick(ev) {
        if (ev.target.tagName !== "INPUT") {
            return;
        }
        ev.stopPropagation();
        this.props.onChange(ev);
    }
}
