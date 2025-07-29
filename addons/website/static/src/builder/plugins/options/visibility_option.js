import { BaseOptionComponent } from "@html_builder/core/utils";

export class VisibilityOption extends BaseOptionComponent {
    static template = "website.VisibilityOption";
    static dependencies = ["visibility", "websiteSession"];
    static selector = "section, .s_hr";

    static cleanForSave = (el, { dependencies }) => {
        dependencies.visibility.cleanForSaveVisibility(el);
    };

    setup() {
        super.setup();
        this.websiteSession = this.dependencies.websiteSession.getSession();
    }
}
