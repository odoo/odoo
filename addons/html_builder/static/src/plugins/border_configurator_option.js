import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";

export class BorderConfigurator extends BaseOptionComponent {
    static template = "html_builder.BorderConfiguratorOption";
    static props = {
        label: { type: String },
        direction: { type: String, optional: true },
        withRoundCorner: { type: Boolean, optional: true },
        withBSClass: { type: Boolean, optional: true },
        action: { type: String, optional: true },
    };
    static defaultProps = {
        withRoundCorner: true,
        withBSClass: true, // TODO remove, and actually configure propertly in caller
        action: "styleAction",
    };

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasBorder: this.hasBorder(editingElement),
        }));
    }
    getStyleActionParam(param) {
        const property = `border-${this.props.direction ? (this.props.direction + "-") : ""}${param}`;
        if (this.props.withBSClass && (param === "width" || param === "radius")) {
            // grep: --box-border-width, --box-border-radius
            return `--box-${property}`;
        }
        return property;
    }
    hasBorder(editingElement) {
        const getAction = this.env.editor.shared.builderActions.getAction;
        const styleActionValue = getAction("styleAction").getValue({
            editingElement,
            params: {
                mainParam: this.getStyleActionParam("width"),
            },
        });
        const values = (styleActionValue || "0").match(/\d+/g);
        return values.some((value) => parseInt(value) > 0);
    }
}
