import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export class AddElementOption extends BaseOptionComponent {
    static template = "website.AddElementOption";
    static props = {
        level: { type: Number, optional: true },
        applyTo: { type: String, optional: true },
    };
    static defaultProps = {
        level: 0,
    };
}
