import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { getCSSVariableValue, getHtmlStyle } from "@html_editor/utils/formatting";
import { registry } from "@web/core/registry";

export class MegaMenuOption extends BaseOptionComponent {
    static id = "mega_menu_option";
    static template = "website.MegaMenuOption";
    static dependencies = [];

    hasHeaderTemplates(headerTemplates) {
        const currentHeaderTemplate = getCSSVariableValue(
            "header-template",
            getHtmlStyle(this.env.editor.document)
        );
        return headerTemplates.includes(currentHeaderTemplate.slice(1, -1));
    }
}
registry.category("website-options").add(MegaMenuOption.id, MegaMenuOption);
