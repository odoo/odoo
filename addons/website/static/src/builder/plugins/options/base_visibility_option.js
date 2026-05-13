import { BaseOptionComponent } from "@html_builder/core/base_option_component";

export class BaseVisibilityOption extends BaseOptionComponent {
    static template = "website.BaseVisibilityOption";
    static dependencies = ["websitePageConfigOptionPlugin"];
    static props = {
        visibilityAction: { type: String, optional: true },
        bgColor: { type: String, optional: true },
        label: { type: String },
        overlay: { type: String, optional: true },
        textColor: { type: String, optional: true },
        tooltip: { type: String, optional: true },
        visibilityOpt: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.hasPageOption = this.dependencies.websitePageConfigOptionPlugin.doesPageOptionExist;
    }
}
