import { BaseOptionComponent } from "@html_builder/core/utils";
import { basicHeaderOptionSettings } from "./basicHeaderOptionSettings";

export class HeaderIconBackgroundOption extends BaseOptionComponent {
    static template = "website.HeaderIconBackgroundOption";
    static editableOnly = basicHeaderOptionSettings.editableOnly;
    static selector = basicHeaderOptionSettings.selector;
    static groups = basicHeaderOptionSettings.groups;
}
