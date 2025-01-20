import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../builder_components/default_builder_components";
import { useDomState } from "../builder_components/utils";

export class BorderConfigurator extends Component {
    static template = "html_builder.BorderConfigurator";
    static components = { ...defaultBuilderComponents };
    static props = {
        label: { type: String },
        direction: { type: String, optional: true },
        applyTo: { type: String },
    };
    setup() {
        this.state = useDomState(() => ({
            hasBorder: this.hasBorder(),
        }));
    }
    getStyleActionParam(param) {
        return `border-${this.props.direction ? this.props.direction + "-" : ""}${param}`;
    }
    hasBorder() {
        const getAction = this.env.editor.shared.builderActions.getAction;
        const editingElement = this.env.getEditingElement().querySelector(this.props.applyTo);
        const styleActionValue = getAction("styleAction").getValue({
            editingElement,
            param: this.getStyleActionParam("width"),
        });
        return parseInt(styleActionValue.match(/\d+/g)[0]) > 0;
    }
}
