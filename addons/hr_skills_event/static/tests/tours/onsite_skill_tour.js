import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("hr_skills_event_onsite_tour", {
    url: "/odoo",
    steps: () => [
        {
            content: "Open Employees app",
            trigger: ".o_app[data-menu-xmlid='hr.menu_hr_root']",
            run: "click",
        },
        {
            content: "Go to test employee",
            trigger: "span:contains('Test Employee')",
            run: "click",
        },
        {
            content: "Go to Resume Tab",
            trigger: "a.nav-link[name='resume']",
            run: "click",
        },
        {
            content: "Open New Resume Line form",
            trigger: "button:contains('Create Resume Lines')",
            run: "click",
        },
        {
            content: "Go to Training Tab",
            trigger: "span.o_selection_badge:contains('Training')",
            run: "click",
        },
        {
            content: "Select Onsite course type",
            trigger: "input[id='radio_field_0_onsite']",
            run: "click",
        },
        {
            content: "Open dropdown menu",
            trigger: "input[id='event_id_0']",
            run: "click",
        },
        {
            content: "Ensure we don't have any options except 'Create'",
            trigger: "div[name='event_id'] ul",
            async run() {
                const liList = document.querySelectorAll("div[name='event_id'] ul>li");
                if (liList.length !== 1) {
                    throw new Error(`Expected 1 item, found ${liList.length}`);
                }
            },
        },
        {
            content: "Open Form to create a new event",
            trigger: "li.o_m2o_dropdown_option_create_edit",
            run: "click",
        },
        {
            content: "Write a name for the event",
            trigger: "textarea[id='name_0']",
            run: "edit Event1",
        },
        {
            content: "Save the event",
            trigger: "div.modal-content:has(h4:contains('Create Onsite Course')) button.o_form_button_save",
            run: "click",
        },
        {
            content: "Select External course type to refresh the event dropdown",
            trigger: "input[id='radio_field_0_external']",
            run: "click",
        },
        {
            content: "Select Onsite course type",
            trigger: "input[id='radio_field_0_onsite']",
            run: "click",
        },
        {
            content: "Open dropdown menu",
            trigger: "input[id='event_id_0']",
            run: "click",
        },
        {
            content: "Ensure we now have the new event as an option",
            trigger: "div[name='event_id'] ul",
            async run() {
                const liList = document.querySelectorAll("div[name='event_id'] ul>li");
                if (liList.length !== 2) {
                    throw new Error(`Expected 2 items, found ${liList.length}`);
                }
            },
        },
        {
            content: "Save the resume line with the event",
            trigger: "div.modal-content:has(h4:contains('New Resume Line')) button.o_form_button_save",
            run: "click",
        },
        {
            content: "Check that the event is correctly displayed in the resume line",
            trigger: ".o_resume_line_title:contains('Event1')",
        },
        {
            content: "Save the employee form",
            trigger: "button.o_form_button_save",
            run: "click",
        },
        {
            content: "Wait for the form to save completely",
            trigger: "body:not(:has(button.o_form_button_save:visible))",
        },

    ],
});
