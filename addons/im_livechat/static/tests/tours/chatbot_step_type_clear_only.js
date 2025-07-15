/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("change_chatbot_step_type", {
    steps: () => [
        {
            content: "Open an existing script",
            trigger: ".o_field_cell[data-tooltip='Clear Answer Test Bot']",
            run: "click",
        },
        {
            content: "Open first step",
            trigger: '.o_row_draggable .o_field_cell:contains("Question")',
            run: "click",
        },
        {
            content: "Change step type to 'text'",
            trigger: 'div[name="step_type"] select',
            run: function (el) {
                el.anchor.value = '"text"';
                el.anchor.dispatchEvent(new Event("change", { bubbles: true }));
            },
        },
        {
            content: "Verify answers cleared",
            trigger: ".btn-primary:contains('Save')",
            run: "click",
        },
        {
            trigger: ".o_form_button_save",
            run: "click",
        },
        {
            trigger: ".o_form_view",
        },
    ],
});
