import { BaseOptionComponent } from "@html_builder/core/utils";

export class VisibilityOption extends BaseOptionComponent {
    static template = "website.VisibilityOption";
    static props = {
        websiteSession: true,
    };
}
