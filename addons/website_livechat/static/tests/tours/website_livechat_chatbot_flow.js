/** @odoo-module */

import { registry } from "@web/core/registry";
import { debounce } from "@web/core/utils/timing";

const messagesContain = (text) => `.o-mail-Message:contains("${text}")`;

registry.category("web_tour.tours").add("website_livechat_chatbot_flow_tour", {
    test: true,
    shadow_dom: ".o-livechat-root",
    steps: () => [
        {
            trigger: messagesContain("Hello! I'm a bot!"),
            run: () => {
                // make chat bot faster for this tour
                const chatbotService = odoo.__WOWL_DEBUG__.root.env.services["im_livechat.chatbot"];
                chatbotService.debouncedProcessUserAnswer = debounce(
                    chatbotService._processUserAnswer.bind(chatbotService),
                    500
                );
            },
        },
        {
            trigger: messagesContain("I help lost visitors find their way."),
            run: () => {}, // check second welcome message is posted
        },
        {
            trigger: messagesContain("How can I help you?"),
            run: () => {}, // check question_selection message is posted
        },
        {
            trigger: 'li:contains("I want to buy the software")',
            run: "click",
        },
        {
            trigger: messagesContain("I want to buy the software"),
            run: () => {}, // check selected option is posted
        },
        {
            trigger: messagesContain("Can you give us your email please?"),
            run: () => {}, // check ask email step following selecting option A
        },
        {
            trigger: ".o-mail-Composer-input ",
            run: "text No, you won't get my email!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: messagesContain(
                "'No, you won't get my email!' does not look like a valid email. Can you please try again?"
            ),
            run: () => {}, // check invalid email detected and the bot asks for a retry
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text okfine@fakeemail.com",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: messagesContain("Your email is validated, thank you!"),
            run: () => {}, // check that this time the email goes through and we proceed to next step
        },
        {
            trigger: messagesContain("Would you mind providing your website address?"),
            run: () => {}, // should ask for website now
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text https://www.fakeaddress.com",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: messagesContain("Great, do you want to leave any feedback for us to improve?"),
            run: () => {}, // should ask for feedback now
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text Yes, actually, I'm glad you asked!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text I think it's outrageous that you ask for all my personal information!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text I will be sure to take this to your manager!",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: messagesContain("Ok bye!"),
            run: () => {}, // last step is displayed
        },
        {
            trigger: ".o-mail-ChatWindow-command[title='Restart Conversation']",
            run: "click",
        },
        {
            trigger: messagesContain("Restarting conversation..."),
            run: () => {}, // check that conversation is properly restarting
        },
        {
            trigger: messagesContain("Hello! I'm a bot!"),
            run: () => {}, // check first welcome message is posted
        },
        {
            trigger: messagesContain("I help lost visitors find their way."),
            run: () => {}, // check second welcome message is posted
        },
        {
            trigger: messagesContain("How can I help you?"),
            run: () => {}, // check question_selection message is posted
        },
        {
            trigger: 'li:contains("Pricing Question")',
            run: "click",
        },
        {
            trigger: messagesContain(
                "For any pricing question, feel free ton contact us at pricing@mycompany.com"
            ),
            run: () => {}, // the path should now go towards 'Pricing Question (first part)'
        },
        {
            trigger: messagesContain("We will reach back to you as soon as we can!"),
            run: () => {}, // the path should now go towards 'Pricing Question (second part)'
        },
        {
            trigger: messagesContain("Would you mind providing your website address?"),
            run: () => {}, // should ask for website now
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text no",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: messagesContain("Great, do you want to leave any feedback for us to improve?"),
            run: () => {}, // should ask for feedback now
        },
        {
            trigger: ".o-mail-Composer-input",
            run: "text no, nothing so say",
        },
        {
            trigger: ".o-mail-Composer-input",
            run() {
                this.$anchor[0].dispatchEvent(
                    new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
                );
            },
        },
        {
            trigger: messagesContain("Ok bye!"),
        },
        {
            // wait for chatbot script to finish.
            trigger: ".o-mail-ChatWindow-command[title='Restart Conversation']",
            run() {},
        },
    ],
});
