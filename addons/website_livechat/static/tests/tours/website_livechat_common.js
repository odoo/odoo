/** @odoo-module **/

/*******************************
 *         Common Steps
 *******************************/

export const start = [
    {
        content: "click on livechat widget",
        trigger: ".o-livechat-LivechatButton",
    },
    {
        content: "Say hello!",
        trigger: ".o-mail-Composer-input",
        run: "text Hello Sir!",
    },
    {
        content: "Send the message",
        trigger: ".o-mail-Composer-input",
        run() {
            this.$anchor[0].dispatchEvent(
                new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
            );
        },
    },
    {
        content: "Verify your message has been typed",
        trigger: ".o-mail-Message:contains('Hello Sir!')",
    },
    {
        content: "Verify there is no duplicates",
        trigger: ".o-mail-Thread",
        run() {
            if (this.$anchor.find(".o-mail-Message:contains('Hello Sir!')").length === 1) {
                $("body").addClass("no_duplicated_message");
            }
        },
    },
    {
        content: "Is your message correctly sent ?",
        trigger: "body.no_duplicated_message",
        shadow_dom: false,
        isCheck: true,
    },
];

export const endDiscussion = [
    {
        content: "Close the chat window",
        trigger: ".o-mail-ChatWindow-command[title*=Close]",
        run: "click",
    },
];

export const feedback = [
    {
        content: "Patching Livechat",
        trigger: "textarea[placeholder='Explain your note']",
        run: function() {
            document.body.classList.add("feedback_sent");
        }
    },
    {
        content: "Type a feedback",
        trigger: "textarea[placeholder='Explain your note']",
        run: "text ;-) This was really helpful. Thanks ;-)!",
    },
    {
        content: "Send the feedback",
        trigger: "button:contains(Send):not(:disabled)",
    },
    {
        content: "Thanks for your feedback",
        trigger: "p:contains('Thank you for your feedback')",
        isCheck: true,
    },
];

export const transcript = [
    {
        content: "Type your email",
        trigger: "input[placeholder='mail@example.com']",
        run: "text deboul@onner.com",
    },
    {
        content: "Send the conversation to your email address",
        trigger: "button[data-action=sendTranscript]",
    },
    {
        content: "Check conversation is sent",
        trigger: ".form-text:contains(The conversation was sent)",
    },
];

export const close = [
    {
        content: "Close the conversation with the x button",
        trigger: ".o-mail-ChatWindow-command[title*=Close]",
        run: "click",
    },
    {
        content: "Check that the button is not displayed anymore",
        trigger: ".o-mail-ChatWindowContainer",
        allowInvisible: true,
        run() {
            if (this.$anchor.find(".o-livechat-livechatButton").length === 0) {
                $("body").addClass("tour_success");
            }
        },
    },
    {
        content: "Is the Test succeded ?",
        trigger: "body.tour_success",
        shadow_dom: false,
        isCheck: true,
    },
];

export const goodRating = [
    {
        content: "Choose Good Rating",
        trigger: `img[src*=rating][alt=5]`,
    },
];

export const okRating = [
    {
        content: "Choose ok Rating",
        trigger: `img[src*=rating][alt=3]`,
    },
];

export const sadRating = [
    {
        content: "Choose bad Rating",
        trigger: `img[src*=rating][alt=1]`,
    },
];
