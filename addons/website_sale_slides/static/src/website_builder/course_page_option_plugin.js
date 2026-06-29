import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class BuyCourseOption extends BaseOptionComponent {
    static template = "website_sales_slides.BuyCourseOption";
    static selector = "main:has(.o_wslides_course_header)";
    static title = _t("Course Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class BuyCourseOptionPlugin extends Plugin {
    static id = "BuyCourseOption";
    resources = {
        builder_options: [BuyCourseOption],
    };
}

registry.category("website-plugins").add(BuyCourseOptionPlugin.id, BuyCourseOptionPlugin);
