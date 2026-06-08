import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { props, t } from "@odoo/owl";

export class BaseVisibilityOption extends BaseOptionComponent {
    static template = "website.BaseVisibilityOption";
    static dependencies = ["websitePageConfigOptionPlugin"];
    props = props({
        visibilityAction: t.string().optional(),
        bgColor: t.string().optional(),
        label: t.string(),
        overlay: t.string().optional(),
        textColor: t.string().optional(),
        tooltip: t.string().optional(),
        visibilityOpt: t.string().optional(),
        level: t.number().optional(0),
    });

    setup() {
        super.setup();
        this.hasPageOption = this.dependencies.websitePageConfigOptionPlugin.doesPageOptionExist;
    }
}
