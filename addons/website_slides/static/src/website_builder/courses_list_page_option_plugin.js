import { after, DEFAULT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const COURSES_LIST_PAGE = DEFAULT;

class CoursesListPageOption extends Plugin {
    static id = "coursesListPageOption";
    resources = {
        builder_options: [
            withSequence(COURSES_LIST_PAGE, {
                template: "website_slides.CoursesListPageOption",
                selector: "main:has(.o_wslides_home_main)",
                editableOnly: false,
                title: _t("Courses Page"),
                groups: ["website.group_website_designer"],
            }),
            withSequence(after(COURSES_LIST_PAGE), {
                template: "website_slides.CoursesListAsidePageOption",
                selector: "main:has(.o_wslides_home_aside_loggedin)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(CoursesListPageOption.id, CoursesListPageOption);
