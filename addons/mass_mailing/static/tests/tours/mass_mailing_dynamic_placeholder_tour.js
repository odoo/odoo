import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add('mass_mailing_dynamic_placeholder_tour', {
    url: '/odoo',
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: "Select the 'Email Marketing' app.",
            trigger: '.o_app[data-menu-xmlid="mass_mailing.mass_mailing_menu_root"]',
            run: "click",
        },
        {
            content: "Click on the create button to create a new mailing.",
            trigger: 'button.o_list_button_add',
            run: "click",
        },
        {
            content: "Fill in Subject",
            trigger: '#subject_0',
            run: "edit Test Dynamic Placeholder",
        },
        {
            trigger: ".o_mailing_template_preview_wrapper",
        },
        {
            content: "Pick the basic theme",
            trigger: '.o_mailing_template_preview_wrapper [data-name="basic"]',
            run: "click",
        },
         {
            content: "Insert text inside editable",
            trigger: ':iframe .odoo-editor-editable',
            async run(actions) {
                await actions.editor(`/`);
                const iframe = document.querySelector("iframe");
                iframe?.contentDocument?.querySelector(".note-editable").dispatchEvent(
                    new InputEvent("input", {
                        inputType: "insertText",
                        data: "/",
                    })
                );
            },
        },
        {
            content: "Click on the the dynamic placeholder powerBox options",
            trigger: '.o-we-command-name:contains("Dynamic Placeholder")',
            run: "click",
        },
        {
            content: "Check if the dynamic placeholder popover is opened",
            trigger: "div.o_model_field_selector_popover",
            run: "click",
        },
        {
            content: "filter the dph result",
            trigger: "div.o_model_field_selector_popover_search input[type='text']",
            run: "edit name",
        },
        {
            content: "Click on the first entry of the dynamic placeholder",
            trigger: 'div.o_model_field_selector_popover button:contains("Company Name")',
            run: "click",
        },
        {
            content: "Enter a default value",
            trigger:
                'div.o_model_field_selector_popover .o_model_field_selector_default_value_input input[type="text"]',
            run: "edit defValue",
        },
        {
            content: "Click on the insert button",
            trigger: "div.o_model_field_selector_popover button:first-child",
            run: "click",
        },
        {
            content: "Ensure the editable contain the dynamic placeholder t tag",
            trigger: `:iframe .note-editable.odoo-editor-editable t[t-out="object.company_name"]:contains("defValue")`,
        },
        {
            content: "Discard form changes",
            trigger: "button.o_form_button_cancel",
            run: "click",
        },
        {
            content: "Wait for the form view to disappear",
            trigger: "body:not(:has(.o_form_sheet))",
        },
    ],
});
