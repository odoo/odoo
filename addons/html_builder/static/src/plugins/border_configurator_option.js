import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { props, t } from "@odoo/owl";

export class BorderConfigurator extends BaseOptionComponent {
    static template = "html_builder.BorderConfiguratorOption";
    static dependencies = ["builderActions"];
    props = props({
        label: t.string(),
        direction: t.string().optional(),
        withRoundCorner: t.boolean().optional(true),
        // TODO remove, and actually configure propertly in caller
        withBSClass: t.boolean().optional(true),
        action: t.string().optional("styleAction"),
        level: t.number().optional(),
    });

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasBorder: this.hasBorder(editingElement),
        }));
    }
    getStyleActionParam(param) {
        const property = `border-${this.props.direction ? this.props.direction + "-" : ""}${param}`;
        if (this.props.withBSClass && (param === "width" || param === "radius")) {
            // grep: --box-border-width, --box-border-radius
            return `--box-${property}`;
        }
        return property;
    }
    hasBorder(editingElement) {
        const { getAction } = this.dependencies.builderActions;
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
