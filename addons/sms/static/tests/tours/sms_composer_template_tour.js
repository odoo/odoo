import { registry } from "@web/core/registry";

/**
 * Data is created by the python test launching this tour.
 * @see sms/tests/test_sms_composer_ui.py
 */
registry.category("web_tour.tours").add("sms_composer_template_tour", {
    steps: () => [
        {
            content: "Focus phone field to display its buttons",
            trigger: ".o_field_widget[name=phone] input",
            run: "click",
        },
        {
            content: "Open SMS composer",
            trigger: ".o_field_widget[name=phone] .o_phone_form_link[title='SMS']",
            run: "click",
        },
        {
            content: "Open template selector",
            trigger: ".modal .mail-composer-template-dropdown-btn",
            run: "click",
        },
        {
            content: "Check save and manage options are available",
            trigger:
                ".mail-composer-template-dropdown.popover:has(.o-dropdown-item:contains(Save as Template)):has(.o-dropdown-item:contains(Manage Templates))",
        },
        {
            content: "Select SMS template",
            trigger:
                '.mail-composer-template-dropdown.popover .mail-composer-template-list .o-dropdown-item:contains("Test SMS template")',
            run: "click",
        },
        {
            content: "Check body is rendered from template",
            trigger: ".modal [name=body] textarea:value(Hello Jane)",
        },
        {
            content: "Open template selector again",
            trigger: ".modal .mail-composer-template-dropdown-btn",
            run: "click",
        },
        {
            content: "Manage templates",
            trigger: ".mail-composer-template-dropdown.popover .o-dropdown-item:contains(Manage Templates)",
            run: "click",
        },
        {
            content: "Check SMS templates list is filtered on contacts",
            trigger: ".o_searchview_facet:contains(res.partner)",
        },
        {
            content: "Check SMS template is listed",
            trigger: ".o_list_renderer .o_data_row:contains(Test SMS template)",
        },
    ],
});
