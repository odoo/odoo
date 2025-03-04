import { Component } from "@odoo/owl";
import { defaultBuilderComponents } from "../core/default_builder_components";
import { useDomState } from "../core/building_blocks/utils";

export class BorderConfigurator extends Component {
    static template = "html_builder.BorderConfiguratorOption";
    static components = { ...defaultBuilderComponents };
    static props = {
        label: { type: String },
        direction: { type: String, optional: true },
        withRoundCorner: { type: Boolean, optional: true },
        withBSClass: { type: Boolean, optional: true },
    };
    static defaultProps = {
        withRoundCorner: true,
        withBSClass: true, // TODO remove, and actually configure propertly in caller
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
            param: {
                mainParam: this.getStyleActionParam("width"),
            },
        });
        const values = (styleActionValue || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
}
