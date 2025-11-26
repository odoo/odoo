import { BaseOptionComponent, useDomState } from "@html_builder/core/utils";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { registry } from "@web/core/registry";

export class MegaMenuOption extends BaseOptionComponent {
    static id = "mega_menu_option";
    static template = "website.MegaMenuOption";
    static dependencies = ["megaMenuOptionPlugin"];

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
registry.category("builder-options").add(MegaMenuOption.id, MegaMenuOption);
