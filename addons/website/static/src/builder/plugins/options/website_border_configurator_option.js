import { BuilderNumberInputSelect } from "@html_builder/core/building_blocks/builder_number_input_select";
import { BuilderNumberSelectItem } from "@html_builder/core/building_blocks/builder_select_item";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { registry } from "@web/core/registry";
import { useDomState } from "@html_builder/core/utils";

const BORDER_RADIUS_OPTIONS = [
    { label: "Small", class: "rounded-1", variable: "border-radius-sm" },
    { label: "Normal", class: "rounded-2", variable: "border-radius" },
    { label: "Large", class: "rounded-3", variable: "border-radius-lg" },
];

export class WebsiteBorderConfigurator extends BorderConfigurator {
    static id = "website_border_configurator";
    static template = "website.WebsiteBorderConfiguratorOption";

    static components = { ...super.components, BuilderNumberInputSelect, BuilderNumberSelectItem };

    setup() {
        super.setup();
        this.borderRadiusOptions = BORDER_RADIUS_OPTIONS;
        this.selectItemState = useDomState((editingElement) => ({
            isAnyActive: this.computeIsAnySelectItemActive(editingElement),
        }));
    }

    get builderActionParam() {
        const classList = this.borderRadiusOptions.map((option) => option.class);
        return {
            ...this.radiusActionParam,
            borderRadiusClasses: classList.join(" "),
        };
    }

    get radiusActionParam() {
        return {
            mainParam: this.getStyleActionParam("radius"),
            extraClass: this.props.withBSClass ? "rounded" : undefined,
        };
    }
    // We only show the theme border-radius suggestions for a limited number of cases.
    get showRoundnessSuggestions() {
        if (this.props.action !== "styleAction") {
            return false;
        }
        return ["--box-border-radius", "border-radius"].includes(this.radiusActionParam.mainParam);
    }

    getOnClick(borderRadiusVariable) {
        return () => this.env.editThemeOption(borderRadiusVariable, "theme-roundness");
    }

    computeIsAnySelectItemActive(editingElement) {
        const action = this.dependencies.builderActions.getAction("setBorderRadiusClass");
        const isAppliedFn = (editingElement, className) =>
            action.isApplied({
                editingElement,
                params: {
                    mainParam: className,
                },
            });
        const classList = this.borderRadiusOptions.map((option) => option.class);
        return classList.some((className) => isAppliedFn(editingElement, className));
    }
}

registry.category("website-options").add(WebsiteBorderConfigurator.id, WebsiteBorderConfigurator);
