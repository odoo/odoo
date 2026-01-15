import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";

export class MegaMenuOption extends BaseOptionComponent {
    static template = "website.MegaMenuOption";
    static dependencies = ["megaMenuOptionPlugin"];
    static selector = ".o_mega_menu";

    setup() {
        super.setup();
        const { getTemplatePrefix } = this.dependencies.megaMenuOptionPlugin;
        this.state = useDomState((el) => ({
            templatePrefix: getTemplatePrefix(el),
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
