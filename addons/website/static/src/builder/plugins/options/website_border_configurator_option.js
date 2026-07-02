import { useDomState } from "@html_builder/core/utils";
import { BorderConfigurator } from "@html_builder/plugins/border_configurator_option";
import { convertValueToUnit } from "@html_builder/utils/utils_css";
import { getHtmlStyle } from "@html_editor/utils/formatting";
import { onMounted, signal } from "@odoo/owl";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { registry } from "@web/core/registry";

const ROUND_CORNER_LABELS = [
    { variable: "border-radius-sm", label: "Small" },
    { variable: "border-radius", label: "Normal" },
    { variable: "border-radius-lg", label: "Large" },
];

export class WebsiteBorderConfigurator extends BorderConfigurator {
    static id = "website_border_configurator";
    static template = "website.WebsiteBorderConfiguratorOption";
    static dependencies = [...super.dependencies, "customizeWebsite"];

    setup() {
        super.setup();
        this.roundCorners = useDomState(() => {
            const suggestions = [];
            for (const suggestion of ROUND_CORNER_LABELS) {
                const variable = this.dependencies.customizeWebsite.getWebsiteVariableValue(
                    suggestion.variable
                );
                const valueInPx = convertValueToUnit(variable, "px", getHtmlStyle(document)) || "0";
                suggestions.push({ ...suggestion, value: valueInPx });
            }
            return { suggestions };
        });
        this.dropdownState = useDropdownState();
        this.inputRef = signal.ref();

        onMounted(() => {
            this.inputRef()?.addEventListener("click", () => {
                if (!this.dropdownState.isOpen) {
                    this.dropdownState.open();
                }
            });
        });
    }
}
registry.category("website-options").add(WebsiteBorderConfigurator.id, WebsiteBorderConfigurator);
