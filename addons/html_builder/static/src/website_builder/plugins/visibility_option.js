import { BaseOptionComponent } from "@html_builder/core/utils";

export class VisibilityOption extends BaseOptionComponent {
    static template = "html_builder.VisibilityOption";
    static props = {
        websiteSession: true,
    };
}
