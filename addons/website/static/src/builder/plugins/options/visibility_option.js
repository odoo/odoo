import { BaseOptionComponent } from "@html_builder/core/utils";

export class VisibilityOption extends BaseOptionComponent {
    static template = "website.VisibilityOption";
    static dependencies = ["visibility", "websiteSession"];
    static selector = "section, .s_hr";

    setup() {
        super.setup();
        this.websiteSession = this.dependencies.websiteSession.getSession();
    }
}
