import { queryAll } from "@odoo/hoot-dom";

/*******************************
 *         Common Steps
 *******************************/

export const start = [
    {
        content: "click on livechat widget",
        trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
        run: "click",
    },
    {
        content: "Say hello!",
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "edit Hello Sir!",
    },
    {
        content: "Send the message",
        trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
        run: "press Enter",
    },
    {
        content: "Verify your message has been typed",
        trigger: ".o-livechat-root:shadow .o-mail-Message:contains('Hello Sir!')",
        run: "click",
    },
    {
        content: "Verify there is no duplicates",
        trigger: ".o-livechat-root:shadow .o-mail-Thread",
        run() {
            const el = queryAll(".o-mail-Message:contains('Hello Sir!')", { root: this.anchor });
            if (el.length === 1) {
                document.querySelector("body").classList.add("no_duplicated_message");
            }
        },
    },
    {
        content: "Is your message correctly sent ?",
        trigger: "body.no_duplicated_message",
    },
];

export const closeChat = [
    {
        content: "Close the chat window",
        trigger: ".o-livechat-root:shadow .o-mail-ChatWindow-command[title*=Close]",
        run: "click",
    },
];

export const confirmnClose = [
    {
        content: "Close confirmation",
        trigger: ".o-livechat-root:shadow .o-livechat-CloseConfirmation-leave",
        run: "click",
    },
];

export const feedback = [
    {
        content: "Patching Livechat",
        trigger: ".o-livechat-root:shadow textarea[placeholder='Explain your note']",
        run: function () {
            document.body.classList.add("feedback_sent");
        },
    },
    {
        content: "Type a feedback",
        trigger: ".o-livechat-root:shadow textarea[placeholder='Explain your note']",
        run: "edit ;-) This was really helpful. Thanks ;-)!",
    },
    {
        content: "Send the feedback",
        trigger: ".o-livechat-root:shadow button:contains(Send):enabled",
        run: "click",
    },
    {
        content: "Thanks for your feedback",
        trigger: ".o-livechat-root:shadow p:contains('Thank you for your feedback')",
    },
];

export const transcript = [
    {
        content: "Type your email",
        trigger: ".o-livechat-root:shadow input[placeholder='mail@example.com']",
        run: "edit deboul@onner.com",
    },
    {
        content: "Send the conversation to your email address",
        trigger: ".o-livechat-root:shadow button[data-action=sendTranscript]",
        run: "click",
    },
    {
        content: "Check conversation is sent",
        trigger: ".o-livechat-root:shadow .form-text:contains(The conversation was sent)",
        run: "click",
    },
];

export const close = [
    {
        content: "Close the conversation with the x button",
        trigger: ".o-livechat-root:shadow .o-mail-ChatWindow-command[title*=Close]",
        run: "click",
    },
    {
        content: "Check that the button is not displayed anymore",
        trigger: ".o-livechat-root:shadow .o-mail-ChatHub:not(:visible)",
        run() {
            if (this.anchor.querySelectorAll(".o-livechat-livechatButton").length) {
                console.error(`There should have no .o-livechat-livechatButton...`);
            }
        },
    },
];

export const goodRating = [
    {
        content: "Choose Good Rating",
        trigger: `.o-livechat-root:shadow img[src*=rating][alt="5"]`,
        run: "click",
    },
];

export const okRating = [
    {
        content: "Choose ok Rating",
        trigger: `.o-livechat-root:shadow img[src*=rating][alt="3"]`,
        run: "click",
    },
];

export const sadRating = [
    {
        content: "Choose bad Rating",
        trigger: `.o-livechat-root:shadow img[src*=rating][alt="1"]`,
        run: "click",
    },
];
