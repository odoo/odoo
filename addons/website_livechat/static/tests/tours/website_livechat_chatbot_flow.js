import { patchWithCleanup } from "@web/../tests/helpers/utils";
import { contains } from "@web/../tests/utils";
import { registry } from "@web/core/registry";
import { Deferred } from "@web/core/utils/concurrency";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";

const messagesContain = (text) => `.o-livechat-root:shadow .o-mail-Message:contains("${text}")`;
let chatbotDelayProcessingDef;

registry.category("web_tour.tours").add("website_livechat_chatbot_flow_tour", {
    steps: () => {
        patchWithCleanup(Chatbot.prototype, {
            // Count the number of times this method is called to check whether the chatbot is regularly
            // checking the user's input in the multi line step until the user finishes typing.
            async _delayThenProcessAnswerAgain(message) {
                chatbotDelayProcessingDef?.resolve();
                return await super._delayThenProcessAnswerAgain(message);
            },
        });
        patchWithCleanup(Chatbot, {
            MESSAGE_DELAY: 0,
            MULTILINE_STEP_DEBOUNCE_DELAY: 2000,
            TYPING_DELAY: 0,
        });
        return [
            {
                // check second welcome message is posted
                trigger: messagesContain("I help lost visitors find their way."),
            },
            {
                trigger: messagesContain("How can I help you?"),
                // check question_selection message is posted and reactions are not
                // available since the thread is not yet persisted
                run() {
                    if (
                        this.anchor.querySelector(
                            ".o-mail-Message-actions [title='Add a Reaction']"
                        )
                    ) {
                        console.error(
                            "Reactions should not be available before thread is persisted."
                        );
                    }
                },
            },
            {
                trigger: '.o-livechat-root:shadow button:contains("I\'d like to buy the software")',
                run: "click",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-ChatWindow",
                // check selected option is posted and reactions are available since
                // the thread has been persisted in the process
                async run() {
                    await contains(".o-mail-Message-actions [title='Add a Reaction']", {
                        target: this.anchor.getRootNode(),
                        parent: [".o-mail-Message", { text: "I'd like to buy the software" }],
                    });
                },
            },
            {
                // check ask email step following selecting option A
                trigger: messagesContain("Can you give us your email please?"),
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input ",
                run: "edit No, you won't get my email!",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                // check invalid email detected and the bot asks for a retry
                trigger: messagesContain(
                    "'No, you won't get my email!' does not look like a valid email. Can you please try again?"
                ),
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit okfine@fakeemail.com",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                // check that this time the email goes through and we proceed to next step
                trigger: messagesContain("Your email is validated, thank you!"),
            },
            {
                // should ask for website now
                trigger: messagesContain("Would you mind providing your website address?"),
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit https://www.fakeaddress.com",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                trigger: messagesContain(
                    "Great, do you want to leave any feedback for us to improve?"
                ),
                // should ask for feedback now
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit Yes, actually, I'm glad you asked!",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit I think it's outrageous that you ask for all my personal information!",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit I will be sure to take this to your manager!",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit I want to say...",
            },
            {
                // Simulate that the user is typing, so the chatbot shouldn't go to the next step
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                async run(helpers) {
                    chatbotDelayProcessingDef = new Deferred();
                    let failTimeout = setTimeout(() => {
                        chatbotDelayProcessingDef.reject(
                            "Chatbot should stay in multi line step when user is typing."
                        );
                    }, 5000);
                    chatbotDelayProcessingDef.then(() => clearTimeout(failTimeout));
                    helpers.edit("Never mind!");
                    await chatbotDelayProcessingDef;
                    chatbotDelayProcessingDef = new Deferred();
                    failTimeout = setTimeout(() => {
                        chatbotDelayProcessingDef.reject(
                            "Chatbot should stay in multi line step if user isn't done typing."
                        );
                    }, 5000);
                    chatbotDelayProcessingDef.then(() => clearTimeout(failTimeout));
                    helpers.edit("Never mind!!!");
                    await chatbotDelayProcessingDef;
                },
            },
            {
                // last step is displayed
                trigger: messagesContain("Ok bye!"),
            },
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow-header [title='Restart Conversation']",
                run: "click",
            },
            {
                // check that conversation is properly restarting
                trigger: messagesContain("Restarting conversation..."),
            },
            {
                // check first welcome message is posted
                trigger: messagesContain("Hello! I'm a bot!"),
            },
            {
                // check second welcome message is posted
                trigger: messagesContain("I help lost visitors find their way."),
            },
            {
                // check question_selection message is posted
                trigger: messagesContain("How can I help you?"),
            },
            {
                trigger: '.o-livechat-root:shadow button:contains("Pricing Question")',
                run: "click",
            },
            {
                // the path should now go towards 'Pricing Question (first part)'
                trigger: messagesContain(
                    "For any pricing question, feel free ton contact us at pricing@mycompany.com"
                ),
            },
            {
                // the path should now go towards 'Pricing Question (second part)'
                trigger: messagesContain("We will reach back to you as soon as we can!"),
            },
            {
                // should ask for website now
                trigger: messagesContain("Would you mind providing your website address?"),
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit no",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                // should ask for feedback now
                trigger: messagesContain(
                    "Great, do you want to leave any feedback for us to improve?"
                ),
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "edit no, nothing so say",
            },
            {
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
                run: "press Enter",
            },
            {
                trigger: messagesContain("Ok bye!"),
                run: "click",
            },
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow-header [title='Restart Conversation']",
                run: "click",
            },
            {
                trigger:
                    ".o-livechat-root:shadow button:contains(I want to speak with an operator)",
                run: "click",
            },
            {
                trigger: messagesContain("I will transfer you to a human."),
            },
            {
                // Wait for the operator to be added: composer is only enabled at that point.
                trigger: ".o-livechat-root:shadow .o-mail-Composer-input:enabled",
            },
        ];
    },
});
