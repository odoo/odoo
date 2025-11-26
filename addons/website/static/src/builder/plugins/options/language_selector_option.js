import { registry } from "@web/core/registry";
import { BaseOptionComponent } from "@html_builder/core/utils";

export class LanguageSelectorOption extends BaseOptionComponent {
    static id = "language_selector_option";
    static template = "website.LanguageSelectorOption";
    // TODO DUAU: check reload target, only 5 occurences put it in props ?
    static reloadTarget = true;
}

registry.category("builder-options").add(LanguageSelectorOption.id, LanguageSelectorOption);
