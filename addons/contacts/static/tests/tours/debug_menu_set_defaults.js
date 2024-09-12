/** @odoo-module **/

    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_service/tour_utils";

    registry.category("web_tour.tours").add('debug_menu_set_defaults', {
        test: true,
        url: '/odoo?debug=1',
        steps: () => [
            ...stepUtils.goToAppSteps('contacts.menu_contacts', "Open the contacts menu"),
            {
                content: "Create a new contact",
                trigger: '.o-kanban-button-new',
                run: "click",
            },
            {
                content: "Check that Company is checked by default, and not Individual",
                trigger: '.o_field_widget[name="company_type"] input[data-value="company"]:checked',
            },
            {
                content: "Select the individual radio button",
                trigger: '.o_field_widget[name="company_type"] input[data-value="person"]',
                run: "click",
            },
            {
                content: "Open the debug menu",
                trigger: '.o_debug_manager button',
                run: "click",
            },
            {
                content: "Click the Set Defaults menu",
                trigger: '.dropdown-item:contains(Set Default Values)',
                run: "click",
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
                run: "click",
            },
            {
                content: "Save the new default",
                trigger: 'footer button:contains(Save default)',
                run: "click",
            },
            {
                content: "Discard the contact creation",
                trigger: 'button.o_form_button_cancel',
                run: "click",
            },
            {
                trigger: '.o_action_manager > .o_kanban_view .o-kanban-button-new',
                run: "click",
            },
            {
                content: "Check that Individual is checked instead of Company",
                trigger: '.o_field_widget[name="company_type"] input[data-value="person"]:checked',
            },
            {
                content: "Discard the contact creation",
                trigger: 'button.o_form_button_cancel',
                run: "click",
            },
            {
                content: "Wait for discard",
                trigger: '.o_control_panel .o-kanban-button-new',
            },
        ]
    });
