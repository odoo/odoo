/** @odoo-module */

import { Component } from "@odoo/owl";
import { CheckBox } from "@web/core/checkbox/checkbox";
import { DomainSelectorDialog } from "@web/core/domain_selector_dialog/domain_selector_dialog";
import { SelectMenu } from "@web/core/select_menu/select_menu";
import { useService } from "@web/core/utils/hooks";

export class Property extends Component {
    static template = "web_studio.Property";
    static components = { CheckBox, SelectMenu, DomainSelectorDialog };
    static defaultProps = {
        childProps: {},
        class: "",
    };
    static props = {
        name: { type: String },
        type: { type: String },
        value: { optional: true },
        onChange: { type: Function, optional: true },
        childProps: { type: Object, optional: true },
        class: { type: String, optional: true },
        isReadonly: { type: Boolean, optional: true },
        slots: {
            type: Object,
            optional: true,
        },
        tooltip: { type: String, optional: true },
        inputAttributes: { type: Object, optional: true },
    };

    setup() {
        this.dialog = useService("dialog");
    }

    get className() {
        const propsClass = this.props.class ? this.props.class : "";
        return `o_web_studio_property_${this.props.name} ${propsClass}`;
    }

    onDomainClicked() {
        this.dialog.add(DomainSelectorDialog, {
            resModel: this.props.childProps.relation,
            domain: this.props.value || "[]",
            isDebugMode: !!this.env.debug,
            onConfirm: (domain) => this.props.onChange(domain, this.props.name),
        });
    }

    onViewOptionChange(value) {
        this.props.onChange(value, this.props.name);
    }
}
