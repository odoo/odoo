import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export class SpacingOption extends BaseOptionComponent {
    static template = "website.SpacingOption";
    static props = {
        applyTo: { type: String, optional: true },
    };
}
