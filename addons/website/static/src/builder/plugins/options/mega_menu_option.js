import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue } from "@html_builder/utils/utils_css";

export class MegaMenuOption extends BaseOptionComponent {
    static template = "website.MegaMenuOption";
    static props = {
        getTemplatePrefix: Function,
    };

    setup() {
        super.setup();
        this.state = useDomState((el) => ({
            templatePrefix: this.props.getTemplatePrefix(el),
        }));
    }

    hasHeaderTemplates(headerTemplates) {
        const currentHeaderTemplate = getCSSVariableValue("header-template");
        return headerTemplates.includes(currentHeaderTemplate.slice(1, -1));
    }
}
