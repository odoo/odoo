import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class CoursePageOptionPlugin extends Plugin {
    static id = "coursePageOption";
    resources = {
        builder_options: [
            withSequence(15, {
                template: "website_sales_slides.CoursePageOption",
                selector: "main:has(.o_wslides_course_header)",
                editableOnly: false,
                title: "Course Page",
            }),
        ],
    };
}

registry.category("website-plugins").add(CoursePageOptionPlugin.id, CoursePageOptionPlugin);
