import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_skills_type_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Open skill type menu",
            trigger: "[data-menu-xmlid='hr.menu_human_resources_configuration']",
            run: "click",
        },
        {
            content: "Open skill type menu",
            trigger: "[data-menu-xmlid='hr_skills.hr_skill_type_menu']",
            run: "click",
        },
        {
            content: "Create a skill type",
            trigger: ".o_list_button_add",
            run: "click",
        },
        {
            content: "Write skill type name",
            trigger: ".o_field_widget[name='name'] input",
            run: "edit Cooking Skill",
        },
        {
            trigger: "div[name=skill_ids] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            trigger: "div[name=skill_ids] div[name=name] input",
            run: "edit Macaroon",
        },
        {
            trigger: "div[name=skill_level_ids] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            trigger: "div[name=skill_level_ids] div[name=name] input",
            run: "edit Beginner",
        },
        {
            trigger: "div[name=skill_level_ids] div[name=default_level] input[type='checkbox']",
            run: "click",
        },
        {
            trigger: "div[name=skill_level_ids] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            trigger: "tr:nth-child(2).o_selected_row div[name=name] input",
            run: "edit Intermediate",
        },
        {
            trigger: "tr:nth-child(2).o_selected_row [name=default_level] input[type='checkbox']",
            run: "click",
        },
        {
            trigger: "div[name=skill_level_ids] .o_field_x2many_list_row_add a",
            run: "click",
        },
        {
            trigger: "tr:nth-child(3).o_selected_row div[name=name] input",
            run: "edit Expert",
        },
        {
            trigger: "tr:nth-child(3).o_selected_row [name=default_level] input[type='checkbox']",
            run: "click",
        },
        {
            trigger: "tr:nth-child(1) [name=default_level] input[type='checkbox']",
            run: "click",
        },
        {
            trigger: "tr:nth-child(2) [name=default_level] input[type='checkbox']",
            run: "click",
        },
        ...stepUtils.saveForm(),
    ],
});
