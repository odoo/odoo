/** @odoo-module **/

import { Component } from "@odoo/owl";
import { useDropdownItemNesting, ClosingMode } from "./dropdown_behaviours/dropdown_nesting";

export class DropdownItem extends Component {
    static template = "web.DropdownItem";
    static props = {
        class: {
            type: [String, Object],
            optional: true,
        },
        onSelected: {
            type: Function,
            optional: true,
        },
        closingMode: {
            type: ClosingMode,
            optional: true,
        },
        attrs: {
            type: Object,
            optional: true,
        },
        slots: { Object, optional: true },
    };
    static defaultProps = {
        closingMode: ClosingMode.AllParents,
        attrs: {},
    };

    setup() {
        this.nesting = useDropdownItemNesting(this.props.closingMode);
    }

    onClick(ev) {
        if (this.props.attrs && this.props.attrs.href) {
            ev.preventDefault();
        }
        this.props.onSelected?.();
        this.nesting.onSelected();
    }
}
