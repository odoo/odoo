import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

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
        const currentHeaderTemplate = getCSSVariableValue(
            "header-template",
            getHtmlStyle(this.env.editor.document)
        );
        return headerTemplates.includes(currentHeaderTemplate.slice(1, -1));
    }
}
