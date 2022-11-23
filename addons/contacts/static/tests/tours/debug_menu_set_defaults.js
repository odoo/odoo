odoo.define('debug_menu_set_defaults.tour', function (require) {
    "use strict";

    var tour = require('web_tour.tour');

    tour.register('debug_menu_set_defaults', {
        test: true,
        url: '/web?debug=1',
    },
        [
            ...tour.stepUtils.goToAppSteps('contacts.menu_contacts', "Open the contacts menu"),
            {
                content: "Create a new contact",
                trigger: '.o-kanban-button-new',
            },
            {
                content: "Check that Company is checked by default, and not Individual",
                trigger: '.o_field_widget[name="company_type"] input[data-value="company"]:checked',
                run: function () {},
            },
            {
                content: "Select the individual radio button",
                trigger: '.o_field_widget[name="company_type"] input[data-value="person"]',
            },
            {
                content: "Open the debug menu",
                trigger: '.o_debug_manager button',
            },
            {
                content: "Click the Set Defaults menu",
                trigger: '.o_debug_manager .dropdown-item:contains(Set Defaults)',
            },
            {
                content: "Choose Company Type = Individual",
                trigger: '#formview_default_fields',
                run: function () {
                    const element_field = document.querySelector('select#formview_default_fields');
                    element_field.value = 'company_type';
                    element_field.dispatchEvent(new Event("change"));
                },
            },
            {
                content: "Check that there are conditions",
                trigger: '#formview_default_conditions',
            },
            {
                content: "Save the new default",
                trigger: 'footer button:contains(Save default)',
            },
            {
                content: "Discard the contact creation",
                trigger: 'button.o_form_button_cancel',
            },
            {
                trigger: '.o-kanban-button-new',
            },
            {
                content: "Check that Individual is checked instead of Company",
                trigger: '.o_field_widget[name="company_type"] input[data-value="person"]:checked',
                run: function () {},
            },
            {
                content: "Discard the contact creation",
                trigger: 'button.o_form_button_cancel',
            },
            {
                content: "Wait for discard",
                trigger: '.o_control_panel .o-kanban-button-new',
                run() {},
            },
        ]
    );

});
