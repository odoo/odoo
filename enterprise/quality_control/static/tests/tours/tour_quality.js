/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_create_new_spreadsheet_from_quality_form", {
    steps: () => [
        {
            trigger: ".o_field_widget[name=spreadsheet_template_id] input",
            run: "click",
        },
        {
            trigger: ".o_m2o_dropdown_option_search_more",
            run: "click",
        },
        {
            trigger: ".o_create_button:contains(New)",
            run: "click",
        },
        {
            trigger: ".o_spreadsheet_container",
            run: () => {},
        },
    ],
});
