import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { useDomState } from "@html_builder/core/utils";
import { props, t } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { CustomizeWebsiteVariableAction } from "../customize_website_plugin";

export function getParsedWeight(value) {
    if (value === "") {
        return null;
    }
    return parseInt(`${value}`.trim());
}

export class FontWeightPicker extends BaseOptionComponent {
    static template = "website.FontWeightPicker";
    props = props({
        variables: t.array(),
        weights: t.array(),
        disabled: t.boolean().optional(false),
    });
}

export class ThemeFontWeightOption extends BaseOptionComponent {
    static template = "website.ThemeFontWeightOption";
    static components = { FontWeightPicker };
    static dependencies = ["customizeWebsite", "themeTab"];
    static props = {
        fontVariable: { type: String },
        regularVariables: { type: Array },
        lightVariables: { type: Array, optional: true },
        boldVariables: { type: Array, optional: true },
    };

    setup() {
        super.setup();
        this.state = useDomState(async () => {
            const fontName = this.dependencies.customizeWebsite.getWebsiteVariableValue(
                this.props.fontVariable
            );
            const availableWeights = await this.dependencies.themeTab.getFontWeights(fontName);
            const regularWeight = this.getCurrentWeight(this.props.regularVariables[0]);
            return {
                availableWeights,
                regularWeight,
            };
        });
    }

    get boldTooltip() {
        return this.isBoldDisabled ? _t("This font is missing font weight") : undefined;
    }

    get filteredLightWeights() {
        return this.getFilteredWeights("light");
    }

    get filteredBoldWeights() {
        return this.getFilteredWeights("bold");
    }

    get isBoldDisabled() {
        return !this.filteredBoldWeights.length;
    }

    getFilteredWeights(type) {
        const { availableWeights, regularWeight } = this.state;
        if (regularWeight === null) {
            return availableWeights;
        }
        return availableWeights.filter(({ value }) =>
            type === "light" ? value <= regularWeight : value >= regularWeight
        );
    }

    getCurrentWeight(weightVariable) {
        if (!weightVariable) {
            return null;
        }
        return (
            getParsedWeight(
                this.dependencies.customizeWebsite.getWebsiteVariableValue(weightVariable)
            ) || null
        );
    }
}

export class CustomizeWebsiteFontWeightAction extends CustomizeWebsiteVariableAction {
    static id = "customizeWebsiteFontWeight";

    getValue({ params }) {
        return super.getValue({ params: { ...params, mainParam: params.mainParam[0] } });
    }

    isApplied({ params, value }) {
        const currentValue = this.getValue({ params });
        return (currentValue === "" ? null : currentValue) === value;
    }

    async apply({ params: { mainParam: variableNames, nullValue = "null" }, value }) {
        const variables = Object.fromEntries(
            variableNames.map((variableName) => [variableName, value])
        );
        await this.dependencies.customizeWebsite.customizeWebsiteVariables(variables, nullValue);
    }
}
