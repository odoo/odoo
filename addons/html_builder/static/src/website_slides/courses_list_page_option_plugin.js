import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

class CoursesListPageOption extends Plugin {
    static id = "coursesListPageOption";
    resources = {
        builder_options: [
            withSequence(15, {
                template: "website_slides.CoursesListPageOption",
                selector: "main:has(.o_wslides_home_main)",
                editableOnly: false,
                title: _t("Courses Page"),
                groups: ["website.group_website_designer"],
            }),
            withSequence(20, {
                template: "website_slides.CoursesListAsidePageOption",
                selector: "main:has(.o_wslides_home_aside_loggedin)",
                editableOnly: false,
                groups: ["website.group_website_designer"],
            }),
        ],
    };
}

registry.category("website-plugins").add(CoursesListPageOption.id, CoursesListPageOption);
