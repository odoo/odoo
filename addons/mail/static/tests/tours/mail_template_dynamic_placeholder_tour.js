import { registry } from "@web/core/registry";
import { delay } from "@web/core/utils/concurrency";
import { stepUtils } from "@web_tour/tour_utils";

registry.category("web_tour.tours").add("mail_template_dynamic_placeholder_tour", {
    url: "/odoo",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Go into the Setting "app"',
            trigger: '.o_app[data-menu-xmlid="base.menu_administration"]',
            run: "click",
        },
        {
            content: "Open email templates",
            trigger: 'button[name="open_mail_templates"]',
            run: "click",
        },
        {
            content: "Create a new email template",
            trigger: "button.o_list_button_add",
            run: "click",
        },
        {
            content: 'Insert # inside "Subject" input',
            trigger: 'div[name="subject"] input[type="text"]',
            run: "edit(no_model_id #)",
        },
        {
            content: 'Select "Contact" model',
            trigger: 'div[name="model_id"] input[type="text"]',
            run: "edit Contact",
        },
        {
            content: "Wait for the autocomplete RPC",
            trigger: 'div[name="model_id"] .ui-autocomplete:contains("Contact")',
            run: async () => {
                await delay(300);
            },
        },
        {
            content: "Click on contact",
            trigger: 'div[name="model_id"] .ui-autocomplete',
            run: async function () {
                const contact = Array.from(
                    document.querySelectorAll(
                        'div[name="model_id"] .ui-autocomplete .dropdown-item'
                    )
                ).find((el) => el.textContent === "Contact");
                await contact.click();
            },
        },
        {
            content: "Wait for the drop down to disappear",
            trigger: 'div[name="model_id"] .o-autocomplete:not(:has(.ui-autocomplete))',
            run: async () => {
                // Ensure the system has registered a correct model value before
                // we try to open the DPH.
                // It seems that the autocomplete validation can be very slow.
                await delay(200);
            },
        },
        {
            content: 'Retry insert # inside "Subject" input',
            trigger: 'div[name="subject"] input[type="text"]',
            run: "edit (yes_model_id) && press #",
        },
        {
            content: "Check if the dynamic placeholder popover is opened",
            trigger: "div.o_model_field_selector_popover",
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
            content: "Wait for the popover to disappear",
            trigger: "body:not(:has(.o_model_field_selector_popover))",
            run: "click",
        },
        {
            content: "Check if subject value was correctly updated",
            trigger: 'div[name="subject"] input[type="text"]',
            run() {
                const subjectValue = this.anchor.value;
                const correctValue = "yes_model_id {{object.company_name|||defValue}}";
                if (subjectValue !== correctValue) {
                    console.error(
                        `Email template should have "${correctValue}" in subject input (actual: ${subjectValue})`
                    );
                }
            },
        },
        {
            content: "Insert text inside editable",
            trigger: ".note-editable.odoo-editor-editable",
            async run(actions) {
                await actions.editor(`/`);
                document.querySelector(".note-editable").dispatchEvent(
                    new InputEvent("input", {
                        inputType: "insertText",
                        data: "/",
                    })
                );
            },
        },
        {
            content: "Click on the the dynamic placeholder powerBox options",
            trigger: "div.o-we-powerbox .o-we-command:contains(Dynamic Placeholder)",
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
            trigger: `.note-editable.odoo-editor-editable t[t-out="object.company_name"]:contains("defValue")`,
        },
        {
            content: 'Type "Push Notification Device" model',
            trigger: 'div[name="model_id"] input[type="text"]',
            run: "edit Push Notification Device",
        },
        {
            content: 'Select "Push Notification Device" model',
            trigger: 'a.dropdown-item:contains("Push Notification Device")',
            run: "click",
        },
        {
            content: "Insert text inside editable",
            trigger: ".note-editable.odoo-editor-editable",
            async run(actions) {
                await actions.editor(`/`);
                document.querySelector(".note-editable").dispatchEvent(
                    new InputEvent("input", {
                        inputType: "insertText",
                        data: "/",
                    })
                );
            },
        },
        {
            content: "Click on the the dynamic placeholder powerBox options",
            trigger: "div.o-we-powerbox .o-we-command:contains(Dynamic Placeholder)",
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
            run: "edit created on",
        },
        {
            content: "Click on the first entry of the dynamic placeholder",
            trigger:
                'div.o_model_field_selector_popover li:first-child button:contains("Created on")',
            run: "click",
        },
        {
            content: "Enter a default value",
            trigger:
                "div.o_model_field_selector_popover .o_model_field_selector_default_value_input input[type='text']",
            run: "edit localTime",
        },
        {
            content: "Click on the insert button",
            trigger: "div.o_model_field_selector_popover button:first-child:contains('Insert)",
            run: "click",
        },
        {
            content: "Ensure the editable contain the dynamic placeholder t tag",
            trigger: `.note-editable.odoo-editor-editable t[t-out="format_datetime(object.create_date, tz=object.partner_id.tz) or 'localTime'"]:contains("localTime")`,
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
