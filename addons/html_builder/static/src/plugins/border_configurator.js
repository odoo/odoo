import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useDomState } from "../core/building_blocks/utils";

export class BorderConfigurator extends Component {
    static template = "html_builder.BorderConfigurator";
    static components = { ...defaultBuilderComponents };
    static props = {
        label: { type: String },
        direction: { type: String, optional: true },
        withRoundCorner: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withRoundCorner: true,
    };

    setup() {
        this.state = useDomState((editingElement) => ({
            hasBorder: this.hasBorder(editingElement),
        }));
    }
    getStyleActionParam(param) {
        return `border-${this.props.direction ? this.props.direction + "-" : ""}${param}`;
    }
    hasBorder(editingElement) {
        if (!editingElement) {
            return false;
        }
        const getAction = this.env.editor.shared.builderActions.getAction;
        const styleActionValue = getAction("styleAction").getValue({
            editingElement,
            param: this.getStyleActionParam("width"),
        });
        return parseInt(styleActionValue.match(/\d+/g)[0]) > 0;
    }
}
