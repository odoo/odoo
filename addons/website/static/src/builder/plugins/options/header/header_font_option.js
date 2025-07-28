import { BaseOptionComponent } from "@html_builder/core/utils";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderFontOption extends BaseOptionComponent {
    static template = "website.HeaderFontOption";
    static editableOnly = basicHeaderOptionSettings.editableOnly;
    static selector = basicHeaderOptionSettings.selector;
    static groups = basicHeaderOptionSettings.groups;
}
