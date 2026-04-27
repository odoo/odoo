/** @odoo-module */

import { Dialog } from "@web/core/dialog/dialog";

import { Component, useRef } from "@odoo/owl";

export class FieldSelectorDialog extends Component {
    static template = "web_studio.FieldSelectorDialog";
    static components = { Dialog };
    static props = {
        close: { type: Function },
        onConfirm: { type: Function },
        fields: { type: Array },
        showNew: { type: Boolean, optional: true },
    };
    static defaultProps = {
        showNew: false,
    };
    setup() {
        this.selectRef = useRef("select");
    }
    onConfirm() {
        const field = this.selectRef.el.value;
        this.props.onConfirm(field);
        this.props.close();
    }
    onCancel() {
        this.props.close();
    }
}
