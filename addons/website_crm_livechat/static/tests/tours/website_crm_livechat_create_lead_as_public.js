/* @odoo-module */

import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("website_crm_livechat.create_lead_as_public", {
    shadow_dom: ".o-livechat-root",
    test: true,
    url: "/contactus",
    steps: () => [
        {
            content: "Open Livechat by clicking its button",
            trigger: ".o-livechat-LivechatButton",
        },{
            content: "Waiting for chatbot to ask for phone number",
            trigger: ".o-mail-Message:contains(Phone number please)",
        },{
            content: "Typing in the following phonenumber: +61 2 8503 8000",
            trigger: ".o-mail-Composer-input",
            run: 'text +61 2 8503 8000',
        },{
            content: "Sending typed in phonenumber i.e. Pressing enter",
            trigger: ".o-mail-Composer-input",
            run() {
                this.anchor.dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
                );
            },
        },{
            content: "Waiting for chatbot to ask for email",
            trigger: ".o-mail-Message:contains(Email please)",
        },{
            content: "Typing in the following phonenumber: bot_should_create_lead_with_this_email@test.com",
            trigger: ".o-mail-Composer-input",
            run: 'text bot_should_create_lead_with_this_email@test.com'
        },{
            content: "Sending typed in email i.e. Pressing enter",
            trigger: ".o-mail-Composer-input",
            run() {
                this.anchor.dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", bubbles: true })
                );
            },
        },{
            content: "Now chatbot should create a new lead and inform us about it.",
            trigger: ".o-mail-Message:contains(Creating lead)",
        }
    ],
});
