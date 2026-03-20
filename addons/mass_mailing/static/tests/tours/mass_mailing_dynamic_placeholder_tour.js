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
            trigger: ":iframe .o_mailing_template_preview_wrapper",
        },
        {
            content: "Pick the basic theme",
            trigger: ':iframe .o_mailing_template_preview_wrapper [data-name="basic"]',
            run: "click",
        },
         {
            content: "Insert text inside editable",
            trigger: ":iframe .odoo-editor-editable .o_mail_no_options",
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
            content: "Click on the the dynamic field powerBox options",
            trigger: ".o-we-powerbox .o-we-command-description:contains(Insert a field)",
            run: "click",
        },
        {
            content: "Check if the dynamic field popover is opened",
            trigger: ".o_model_field_selector_value",
            run: "click",
        },
        {
            content: "Filter the dynamic field result",
            trigger: ".o_model_field_selector_popover_search input",
            run: "edit name",
        },
        {
            content: "Click on the first entry of the dynamic field",
            trigger: '.o_model_field_selector_popover_item_name:contains("Company Name")',
            run: "click",
        },
        {
            content: "Enter a default value",
            trigger: ".o-dynamic-field-popover input[name='label_value']",
            run: "edit defValue",
        },
        {
            content: "Click on the insert button",
            trigger: ".o-dynamic-field-popover button.btn-primary",
            run: "click",
        },
        {
            content: "Ensure the editable contain the dynamic field t tag",
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
