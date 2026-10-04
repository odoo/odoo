import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { useProps, t } from "@odoo/owl";

const BORDER_RADIUS_OPTIONS = [
    { label: "Small", class: "rounded-1", variable: "border-radius-sm" },
    { label: "Normal", class: "rounded-2", variable: "border-radius" },
    { label: "Large", class: "rounded-3", variable: "border-radius-lg" },
];

export class BorderConfigurator extends BaseOptionComponent {
    static template = "html_builder.BorderConfiguratorOption";
    static dependencies = ["builderActions"];
    props = useProps({
        label: t.string(),
        direction: t.string().optional(),
        withRoundCorner: t.boolean().optional(true),
        // TODO remove, and actually configure propertly in caller
        withBSClass: t.boolean().optional(true),
        action: t.string().optional("styleAction"),
        level: t.number().optional(),
        showSuggestions: t.boolean().optional(true),
    });

    setup() {
        super.setup();
        this.state = useDomState((editingElement) => ({
            hasBorder: this.hasBorder(editingElement),
        }));
        this.borderRadiusOptions = this.showSuggestions() ? BORDER_RADIUS_OPTIONS : [];
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
    getOnClick(variable) {
        return () => this.env.editThemeOption(variable, "theme-roundness");
    }
    showSuggestions() {
        return (
            this.props.showSuggestions &&
            this.props.action === "styleAction" &&
            ["--box-border-radius", "border-radius"].includes(this.radiusActionParam.mainParam)
        );
    }
    get radiusActionParam() {
        return {
            mainParam: this.getStyleActionParam("radius"),
            extraClass: this.props.withBSClass ? "rounded" : undefined,
        };
    }
}
