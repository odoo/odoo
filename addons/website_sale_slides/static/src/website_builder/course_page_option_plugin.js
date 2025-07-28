import { BaseOptionComponent } from "@html_builder/core/utils";
import { Plugin } from "@html_editor/plugin";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export class CoursePageOption extends BaseOptionComponent {
    static template = "website_sales_slides.CoursePageOption";
    static selector = "main:has(.o_wslides_course_header)";
    static title = _t("Course Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

class CoursePageOptionPlugin extends Plugin {
    static id = "coursePageOption";
    resources = {
        builder_options: [CoursePageOption],
    };
}

registry.category("website-plugins").add(CoursePageOptionPlugin.id, CoursePageOptionPlugin);
