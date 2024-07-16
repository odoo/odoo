/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add('hr_skills_tour', {
    test: true,
    url: '/web',
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
        content: "Add a new Resume experience",
        trigger: ".o_field_resume_one2many tr.o_resume_group_header button.btn-secondary",
        run: "click",
    },
    {
        content: "Enter some company name",
        trigger: ".modal:contains(new resume line) .modal-body .o_field_widget[name='name'] input",
        in_modal: false,
        run: "edit Mamie Rock",
    },
    {
        content: "Set start date",
        trigger: ".modal:contains(new resume line) .o_field_widget[name='date_start'] input",
        in_modal: false,
        run: "edit 12/05/2017",
    },
    {
        content: "Give some description",
        trigger: ".modal:contains(new resume line) .o_field_widget[name='description'] textarea",
        in_modal: false,
        run: "edit Sang some songs and played some music",
    },
    {
        content: "Save it",
        trigger: ".modal:contains(new resume line) .o_form_button_save:contains(save)",
        in_modal: false,
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
        in_modal: false,
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
        in_modal: false,
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
        trigger: ".modal:contains(select skills) .o_field_widget[name='skill_type_id'] label:contains('Best Music')",
        in_modal: false,
        run: "click",
    },
    {
        content: "Select a song",
        trigger: ".modal:contains(select skills) .o_field_widget[name='skill_id'] input",
        in_modal: false,
        run: "edit Fortun",
    },
    {
        content: "Choose the song",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Fortunate Son")',
        run: "click",
    },
    {
        content: "Select a level",
        trigger: ".modal:contains(select skills) .o_field_widget[name='skill_level_id'] input",
        in_modal: false,
        run: "edit Level",
    },
    {
        content: "Choose the level",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Level 2")',
        run: "click",
    },
    {
        content: "Save new skill",
        trigger: ".modal:contains(select skills) .o_form_button_save:contains(save & close)",
        in_modal: false,
        run: "click",
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
        content: "Select a song", // "Music" should be already selected
        trigger: ".modal:contains(select skills) .o_field_widget[name='skill_id'] input",
        in_modal: false,
        run: "edit Mary",
    },
    {
        content: "Choose the song",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Oh Mary")',
        run: "click",
    },
    {
        content: "Select a level",
        trigger: ".modal:contains(select skills) .o_field_widget[name='skill_level_id'] input",
        in_modal: false,
        run: "edit Level 7",
    },
    {
        content: "Choose the level",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Level 7")',
        run: "click",
    },
    {
        content: "Save new skill",
        trigger: ".modal:contains(select skills) .o_form_button_save:contains(save & close)",
        in_modal: false,
        run: "click",
    },
    {
        content: "Check if item is added",
        trigger: ".o_data_row td.o_data_cell:contains('Oh Mary')",
    },
    ...stepUtils.saveForm(),
]});
