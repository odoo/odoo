import { BaseOptionComponent } from "@html_builder/core/utils";
import { registry } from "@web/core/registry";

export class VisibilityOption extends BaseOptionComponent {
    static id = "visibility_option";
    static template = "website.VisibilityOption";
    static dependencies = ["websiteSession"];

    setup() {
        super.setup();
        this.websiteSession = this.dependencies.websiteSession.getSession();
    }
}

registry.category("website-options").add(VisibilityOption.id, VisibilityOption);
