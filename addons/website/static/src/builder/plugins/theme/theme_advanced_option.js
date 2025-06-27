import { BaseOptionComponent } from "@html_builder/core/utils";

export class ThemeAdvancedOption extends BaseOptionComponent {
    static template = "website.ThemeAdvancedOption";
    static props = {
        grays: Object,
    };
}
