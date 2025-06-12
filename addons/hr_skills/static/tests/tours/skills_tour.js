import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("hr_skills_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Create a new employee",
            trigger: ".o-kanban-button-new",
            run: "click",
        },
        {
            content: "Pick a name",
            trigger: ".o_field_widget[name='name'] input",
            run: "edit Jony McHallyFace",
        },
        {
            content: "Save",
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            content: "Add Experience",
            trigger: ".nav-link:contains('Resume')",
            run: "click",
        },
        {
            content: "Add a new Resume experience",
            trigger: ".o_field_resume_one2many tr.o_resume_group_header button.btn-secondary",
            run: "click",
        },
        {
            content: "Enter some company name",
            trigger:
                ".modal:contains(new resume line) .modal-body .o_field_widget[name='name'] input",
            run: "edit Mamie Rock",
        },
        {
            content: "Set start date",
            trigger: ".modal:contains(new resume line) .o_field_widget[name='date_start'] input",
            run: "edit 12/05/2017",
        },
        {
            content: "Give some description",
            trigger: `.modal:contains(new resume line) .o_field_html[name='description'] div.o-paragraph`,
            run: "editor Sang some songs and played some music",
        },
        {
            content: "Save it",
            trigger: ".modal:contains(new resume line) .o_form_button_save:contains(save)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal:contains(new resume line)))",
        },
        {
            content: "Edit newly created experience",
            trigger: ".o_resume_line_title:contains(Mamie Rock)",
            run: "click",
        },
        {
            content: "Change type",
            trigger: ".modal:contains(new resume line) .o_field_widget[name='line_type_id'] input",
            run: "edit Experience",
        },
        {
            content: "Choose experience",
            trigger: '.ui-autocomplete .ui-menu-item a:contains("Experience")',
            run: "click",
        },
        {
            content: "Save experience change",
            trigger: ".modal:contains(new resume line) .o_form_button_save:contains(save)",
            run: "click",
        },
        {
            trigger: "body:not(:has(.modal:contains(new resume line)))",
        },
        {
            content: "Add a new Skill",
            trigger: ".o_field_skills_one2many button:contains('Pick a skill from the list')",
            run: "click",
        },
        {
            content: "Select Music",
            trigger: ".o_field_widget[name='skill_type_id'] span:contains('Best Music')",
            run: "click",
        },
        {
            content: "Choose the song",
            trigger: ".o_field_widget[name='skill_id'] span:contains('Fortunate Son')",
            run: "click",
        },
        {
            content: "Choose the level",
            trigger: ".o_field_widget[name='skill_level_id'] span:contains('Level 2')",
            run: "click",
        },
        {
            content: "Save new skill",
            trigger: ".modal:contains(update skills) .o_form_button_save:contains(save & close)",
            run: "click",
        },
        {
            content:
                "Wait the new skill is completely saved. Ensure also the modal is closed before open a new one.",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Check if item is added",
            trigger: ".o_data_row td.o_data_cell:contains('Fortunate Son')",
        },
        {
            content: "Add a new Skill",
            trigger: ".o_field_skills_one2many button:contains('ADD')",
            run: "click",
        },
        {
            content: "Select Certification",
            trigger: ".o_field_widget[name='skill_type_id'] span:contains('Music Certification')",
            run: "click",
        },
        {
            content: "Choose the instrument",
            trigger: ".o_field_widget[name='skill_id'] span:contains('Piano')",
            run: "click",
        },
        {
            content: "Choose the level",
            trigger: "div[name='valid_from'] button",
            run: "click",
        },
        {
            content: "Choose the level",
            trigger: ".o_field_widget[name='valid_from'] input",
            run: "edit 02/03/2025",
        },
        {
            content: "Choose the level",
            trigger: ".o_field_widget[name='valid_to']",
            run: "click",
        },
        {
            content: "Choose the level",
            trigger: ".o_field_widget[name='valid_to'] input",
            run: "edit 03/04/2025",
        },
        {
            content: "Save new skill",
            trigger: ".modal:contains(update skills) .o_form_button_save:contains(save & close)",
            run: "click",
        },
        {
            content: "Wait the new skill is completely saved",
            trigger: "body:not(:has(.modal))",
        },
        {
            content: "Check if item is added",
            trigger: ".o_data_row td.o_data_cell:contains('Piano')",
        },
        ...stepUtils.saveForm(),
    ],
});
