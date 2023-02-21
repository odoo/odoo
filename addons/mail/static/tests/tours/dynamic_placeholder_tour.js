/** @odoo-module **/

import { registry } from "@web/core/registry";
import { stepUtils } from "@web_tour/js/tour_step_utils";

registry.category("web_tour.tours").add("mail/static/tests/tours/dynamic_placeholder_tour.js", {
    url: "/web",
    test: true,
    steps: [
        stepUtils.showAppsMenuItem(),
        {
            content: 'Go into the Setting "app"',
            trigger: '.o_app[data-menu-xmlid="base.menu_administration"]',
        },
        {
            content: "Open technical dropdown",
            trigger: 'button[data-menu-xmlid="base.menu_custom"]',
        },
        {
            content: "Select email templates",
            trigger: 'a[data-menu-xmlid="mail.menu_email_templates"]',
        },
        {
            content: "Create a new email template",
            trigger: "button.o_list_button_add",
        },
        {
            content: 'Insert # inside "Subject" input',
            trigger: 'div[name="subject"] input[type="text"]',
            run(actions) {
                actions.text(`no_model_id #`, this.$anchor);
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { bubbles: true, key: "#" })
                );
            },
        },
        {
            content: "Check subject kept the # char And an error notification appear",
            trigger: 'div[name="subject"] input[type="text"]',
            run() {
                const subjectValue = this.$anchor[0].value;
                if (subjectValue !== "no_model_id #") {
                    console.error(
                        `Email template should have "#" in subject input (actual: ${subjectValue})`
                    );
                }

                const notification = document.querySelector(
                    "div.o_notification_manager .o_notification .o_notification_content"
                );
                if (
                    !notification ||
                    notification.textContent !==
                        "You need to select a baseModel before opening the dynamic placeholder selector."
                ) {
                    console.error(`Email template did not show correct notification.`);
                }
            },
        },
        {
            content: 'Select "Contact" model',
            trigger: 'div[name="model_id"] input[type="text"]',
            run: "text Contact",
        },
        {
            content: "Wait for model to load and click on contact",
            trigger: 'div[name="model_id"] .ui-autocomplete .dropdown-item:not(:has(.fa-spin))',
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
            run: function () {},
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
            trigger: "div.o_field_selector_popover",
            run: function () {},
        },
        {
            content: "Click on the first entry of the dynamic placeholder",
            trigger: "div.o_field_selector_popover li:first-child",
        },
        {
            content: "Enter a default value",
            trigger:
                'div.o_field_selector_popover .o_field_selector_default_value_input input[type="text"]',
            run: "text defValue",
        },
        {
            content: "Click on the the dynamic placeholder default value",
            trigger: "div.o_field_selector_popover li:first-child",
        },
        {
            content: "Wait for the popover to disappear",
            trigger: "div.o_popover_container:empty",
            run: function () {},
        },
        {
            content: "Check if subject value was correclty updated",
            trigger: 'div[name="subject"] input[type="text"]',
            run() {
                const subjectValue = this.$anchor[0].value;
                const correctValue =
                    "yes_model_id {{object.activity_exception_decoration or '''defValue'''}}";
                if (subjectValue !== correctValue) {
                    console.error(
                        `Email template should have "${correctValue}" in subject input (actual: ${subjectValue})`
                    );
                }
            },
        },
    ],
});
