import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { registry } from "@web/core/registry";

class CoursesListPageOption extends Plugin {
    static id = "coursesListPageOption";
    resources = {
        builder_options: [
            withSequence(15, {
                template: "website_slides.CoursesListPageOption",
                selector: "main:has(.o_wslides_home_main)",
                editableOnly: false,
                title: "Courses Page",
            }),
            withSequence(20, {
                template: "website_slides.CoursesListAsidePageOption",
                selector: "main:has(.o_wslides_home_aside_loggedin)",
                editableOnly: false,
            }),
        ],
    };
}

registry.category("website-plugins").add(CoursesListPageOption.id, CoursesListPageOption);
