import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class CoursePageOptionPlugin extends Plugin {
    static id = "coursePageOption";
    resources = {
        builder_options: [
            withSequence(15, {
                template: "website_sales_slides.CoursePageOption",
                selector: "main:has(.o_wslides_course_header)",
                editableOnly: false,
                title: _t("Course Page"),
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(CoursePageOptionPlugin.id, CoursePageOptionPlugin);
