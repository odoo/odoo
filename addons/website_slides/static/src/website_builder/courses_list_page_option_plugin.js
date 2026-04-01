import { BaseOptionComponent } from "@html_builder/core/utils";
import { after, DEFAULT } from "@html_builder/utils/option_sequence";
import { Plugin } from "@html_editor/plugin";
import { withSequence } from "@html_editor/utils/resource";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const COURSES_LIST_PAGE = DEFAULT;

export class CoursesListPageOption extends BaseOptionComponent {
    static template = "website_slides.CoursesListPageOption";
    static selector = "main:has(.o_wslides_home_main)";
    static title = _t("Courses Page");
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class CoursesListAsidePageOption extends BaseOptionComponent {
    static template = "website_slides.CoursesListAsidePageOption";
    static selector = "main:has(.o_wslides_home_aside_loggedin)";
    static groups = ["website.group_website_designer"];
    static editableOnly = false;
}

export class CoursesListPageOptionPlugin extends Plugin {
    static id = "coursesListPageOption";
    resources = {
        builder_options: [
            withSequence(COURSES_LIST_PAGE, CoursesListPageOption),
            withSequence(after(COURSES_LIST_PAGE), CoursesListAsidePageOption),
        ],
    };
}

registry
    .category("website-plugins")
    .add(CoursesListPageOptionPlugin.id, CoursesListPageOptionPlugin);
