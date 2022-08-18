/** @odoo-module **/

import tour from 'web_tour.tour';

tour.register('hr_skills_tour', {
    test: true,
    url: '/web',
}, [
    tour.stepUtils.showAppsMenuItem(),
    {
        content: "Open Employees app",
        trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
    },
    {
        content: "Create a new employee",
        trigger: ".o-kanban-button-new",
    },
    {
        content: "Pick a name",
        trigger: ".o_field_widget[name='name'] input",
        run: "text Jony McHallyFace",
    },
    {
        content: "Save",
        trigger: ".o_form_button_save",
    },
    {
        content: "Switch to edit",
        trigger: ".o_form_button_edit",
    },
    {
        content: "Add a new Resume experience",
        trigger: ".o_field_resume_one2many tr.o_resume_group_header button.btn-secondary",
    },
    {
        content: "Enter some company name",
        trigger: ".o_form_view_dialog .o_field_widget[name='name'] input",
        run: "text Mamie Rock",
    },
    {
        content: "Set start date",
        trigger: ".o_field_widget[name='date_start'] input",
        run: "text 12/05/2017",
    },
    {
        content: "Give some description",
        trigger: ".o_field_widget[name='description'] textarea",
        run: "text Sang some songs and played some music",
    },
    {
        content: "Save it",
        trigger: ".o_form_button_save",
        run: "click",
    },
    {
        content: "Edit newly created experience",
        trigger: ".o_resume_line_title:contains('Mamie Rock')",
        run: "click",
    },
    {
        content: "Change type",
        trigger: ".o_field_widget[name='line_type_id'] input",
        run: "text Experience",
    },
    {
        content: "Choose experience",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Experience")',
        run: "click",
    },
    {
        content: "Save experience change",
        trigger: ".o_form_button_save",
        in_modal: true,
        run: "click",
    },
    {
        content: "Add a new Skill",
        trigger: ".o_field_skills_one2many button:contains('Create a new entry')",
    },
    {
        content: "Select Music",
        trigger: ".o_field_widget[name='skill_type_id'] label:contains('Best Music')",
        run: "click",
    },
    {
        content: "Select a song",
        trigger: ".o_field_widget[name='skill_id'] input",
        run: "text Fortun",
    },
    {
        content: "Choose the song",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Fortunate Son")',
        run: "click",
    },
    {
        content: "Select a level",
        trigger: ".o_field_widget[name='skill_level_id'] input",
        run: "text Level",
    },
    {
        content: "Choose the level",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Level 2")',
        run: "click",
    },
    {
        content: "Save new skill",
        trigger: ".o_form_button_save",
        in_modal: true,
        run: "click",
    },
    {
        content: "Add a new Skill",
        trigger: ".o_field_skills_one2many button:contains('ADD')",
    },
    {
        content: "Select a song", // "Music" should be already selected
        trigger: ".o_field_widget[name='skill_id'] input",
        run: "text Mary",
    },
    {
        content: "Choose the song",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Oh Mary")',
        run: "click",
    },
    {
        content: "Select a level",
        trigger: ".o_field_widget[name='skill_level_id'] input",
        run: "text Level 7",
    },
    {
        content: "Choose the level",
        trigger: '.ui-autocomplete .ui-menu-item a:contains("Level 7")',
        run: "click",
    },
    {
        content: "Save new skill",
        trigger: ".o_form_button_save",
        in_modal: true,
        run: "click",
    },
    ...tour.stepUtils.saveForm(),
    {
        content: "Go back to employees",
        trigger: 'a[data-menu-xmlid="hr.menu_hr_root"]',
        run: "click",
    }
]);
