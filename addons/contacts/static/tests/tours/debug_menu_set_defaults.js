    import { registry } from "@web/core/registry";
    import { stepUtils } from "@web_tour/tour_utils";
    import { delay } from "@web/core/utils/concurrency";

    registry.category("web_tour.tours").add('debug_menu_set_defaults', {
        url: '/odoo?debug=1',
        steps: () => [
            ...stepUtils.goToAppSteps('contacts.menu_contacts', "Open the contacts menu"),
            {
                content: "Create a new contact",
                trigger: '.o_list_button_add',
                run: "click",
            },
            {
                content: "Check that Job Position is empty",
                trigger: '.o_field_widget[name="function"] input#function_0',
                run: function () {
                    const function_input = document.querySelector('#function_0')
                    if (function_input.value) {
                        console.error('Job Position should be empty');
                    }
                }
            },
            {
                content: "Enter a Job Position",
                trigger: '.o_field_widget[name="function"] input#function_0',
                run: "edit Default Position",
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
                content: "Choose Job Position = Default Position",
                trigger: '#formview_default_fields',
                run: function () {
                    const element_field = document.querySelector('select#formview_default_fields');
                    element_field.value = 'function';
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
                trigger: '.o_action_manager > .o_list_view .o_list_button_add',
                run: "click",
            },
            {
                content: "Check that Job Position is set as 'Default Position'",
                trigger: '.o_field_widget[name="function"] input#function_0',
                run: async () => {
                    await delay(500);
                    const function_input = document.querySelector('#function_0')
                    if (function_input.value !== "Default Position") {
                        console.error('Job Position should be set as "Default Position"');
                    }
                }
            },
            {
                content: "Discard the contact creation",
                trigger: 'button.o_form_button_cancel',
                run: "click",
            },
            {
                content: "Wait for discard",
                trigger: '.o_control_panel .o_list_button_add',
            },
        ]
    });
