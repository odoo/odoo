import { BaseOptionComponent } from "@html_builder/core/utils";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderTemplateOption extends BaseOptionComponent {
    static template = "website.HeaderTemplateOption";
    static editableOnly = basicHeaderOptionSettings.editableOnly;
    static selector = basicHeaderOptionSettings.selector;
    static groups = basicHeaderOptionSettings.groups;

    hasSomeOptions(opts) {
        return opts.some((opt) => this.isActiveItem(opt));
    }
}
