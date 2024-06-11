/* @odoo-module */

import { registry } from "@web/core/registry";
import { contains } from "@web/../tests/utils";
import { stepUtils } from "@web_tour/tour_service/tour_utils";

registry.category("web_tour.tours").add("mail_template_dynamic_placeholder_tour", {
    test: true,
    url: "/web",
    steps: () => [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Go into the Setting "app"',
            trigger: '.o_app[data-menu-xmlid="base.menu_administration"]',
        },
        {
            content: "Open email templates",
            trigger: 'button[name="open_mail_templates"]',
        },
        {
            content: "Create a new email template",
            trigger: "button.o_list_button_add",
        },
        {
            content: 'Insert # inside "Subject" input',
            trigger: 'div[name="subject"] input[type="text"]',
            async run(actions) {
                actions.text(`no_model_id #`, this.$anchor);
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { bubbles: true, key: "#" })
                );
                await contains("div[name='subject'] input[type='text']", {
                    value: "no_model_id #",
                });
                await contains(".o_notification", {
                    text: "You need to select a model before opening the dynamic placeholder selector.",
                });
            },
        },
        {
            content: 'Select "Contact" model',
            trigger: 'div[name="model_id"] input[type="text"]',
            run: "text Contact",
        },
        {
            content: "Wait for the autocomplete RPC",
            trigger: 'div[name="model_id"] .ui-autocomplete:contains("Contact")',
            isCheck: true,
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
                await new Promise((r) => setTimeout(r, 200));
            },
        },
        {
            content: 'Retry insert # inside "Subject" input',
            trigger: 'div[name="subject"] input[type="text"]',
            run(actions) {
                actions.text(`yes_model_id #`, this.$anchor);
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { bubbles: true, key: "#" })
                );
            },
        },
        {
            content: "Check if the dynamic placeholder popover is opened",
            trigger: "div.o_model_field_selector_popover",
            isCheck: true,
        },
        {
            content: "filter the dph result",
            trigger: "div.o_model_field_selector_popover_search input[type='text']",
            run: "text name",
        },
        {
            content: "Click on the first entry of the dynamic placeholder",
            trigger: 'div.o_model_field_selector_popover li:first-child button:contains("Name")',
        },
        {
            content: "Enter a default value",
            trigger:
                'div.o_model_field_selector_popover .o_model_field_selector_default_value_input input[type="text"]',
            run: "text defValue",
        },
        {
            content: "Click on the the dynamic placeholder default value",
            trigger: "div.o_model_field_selector_popover li:first-child button",
        },
        {
            content: "Wait for the popover to disappear",
            trigger: "body:not(:has(.o_model_field_selector_popover))",
        },
        {
            content: "Check if subject value was correclty updated",
            trigger: 'div[name="subject"] input[type="text"]',
            run() {
                const subjectValue = this.$anchor[0].value;
                const correctValue = "yes_model_id {{object.name or '''defValue'''}}";
                if (subjectValue !== correctValue) {
                    console.error(
                        `Email template should have "${correctValue}" in subject input (actual: ${subjectValue})`
                    );
                }
            },
        },
        {
            content: "Insert tesxt inside editable",
            trigger: ".note-editable.odoo-editor-editable",
            run(actions) {
                actions.text(`/`, this.$anchor);
                document.querySelector(".note-editable").dispatchEvent(
                    new InputEvent("input", {
                        inputType: "insertText",
                        data: "/",
                    })
                );
            },
        },
        {
            content: "Click on the the dynamic placeholder commandBar options",
            trigger: "div.oe-powerbox-commandWrapper:contains(Dynamic Placeholder)",
        },
        {
            content: "Check if the dynamic placeholder popover is opened",
            trigger: "div.o_model_field_selector_popover",
        },
        {
            content: "filter the dph result",
            trigger: "div.o_model_field_selector_popover_search input[type='text']",
            run: "text name",
        },
        {
            content: "Click on the first entry of the dynamic placeholder",
            trigger: 'div.o_model_field_selector_popover li:first-child button:contains("Name")',
        },
        {
            content: "Enter a default value",
            trigger:
                'div.o_model_field_selector_popover .o_model_field_selector_default_value_input input[type="text"]',
            run: "text defValue",
        },
        {
            content: "Click on the the dynamic placeholder default value",
            trigger: "div.o_model_field_selector_popover li:first-child button",
        },
        {
            content: "Ensure the editable contain the dynamic placeholder t tag",
            trigger:
                ".note-editable.odoo-editor-editable t[t-out=\"object.name or '''defValue'''\"]",
        },
        {
            content: "Discard form changes",
            trigger: "button.o_form_button_cancel",
        },
        {
            content: "Wait for the form view to disappear",
            trigger: "body:not(:has(.o_form_sheet))",
            isCheck: true,
        },
    ],
});
