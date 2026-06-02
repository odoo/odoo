import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";

const trigger = `.o-livechat-root:shadow .o-mail-Composer-input`;
const messagesContain = (text) =>
    `.o-livechat-root:shadow .o-mail-Message:last:contains("${text}")`;
const postMessage = (text) => ({
    trigger,
    run: `edit ${text} && press Enter`,
});

let chatbotDelayProcessingDef;

registry.category("web_tour.tours").add("website_livechat_chatbot_flow_tour", {
    steps: () => {
        patch(Chatbot.prototype, {
            // Count the number of times this method is called to check whether the chatbot is regularly
            // checking the user's input in the multi line step until the user finishes typing.
            async _delayThenProcessAnswerAgain(message) {
                chatbotDelayProcessingDef?.resolve();
                return await super._delayThenProcessAnswerAgain(message);
            },
        });
        patch(Chatbot, {
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
            },
            {
                content: "Reactions should not be available before thread is persisted.",
                trigger: `body:not(:has(.o-mail-Message-actions [title='Add a Reaction']))`,
            },
            {
                trigger: '.o-livechat-root:shadow button:contains("I\'d like to buy the software")',
                run: "click",
            },
            {
                // check selected option is posted and reactions are available since
                // the thread has been persisted in the process
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow .o-mail-Message:has(.o-mail-Message-actions [title='Add a Reaction']):contains('I\\'d like to buy the software')",
            },
            {
                // check ask email step following selecting option A
                trigger: messagesContain("Can you give us your email please?"),
            },
            postMessage("No, you won't get my email!"),
            {
                // check invalid email detected and the bot asks for a retry
                trigger: messagesContain(
                    "'No, you won't get my email!' does not look like a valid email. Can you please try again?"
                ),
            },
            postMessage("okfine@fakeemail.com"),
            {
                // check that this time the email goes through and we proceed to next step
                trigger: messagesContain("Your email is validated, thank you!"),
            },
            {
                trigger: messagesContain("Can you give us your phone number please?"),
            },
            postMessage("123456"),
            {
                trigger: messagesContain(
                    "'123456' does not look like a valid phone number. Can you please try again?"
                ),
            },
            postMessage("+919876543210"),
            {
                trigger: messagesContain("Your phone number is validated. thank you!"),
            },
            {
                // should ask for website now
                trigger: messagesContain("Would you mind providing your website address?"),
            },
            postMessage("https://www.fakeaddress.com"),
            {
                trigger: messagesContain(
                    "Great, do you want to leave any feedback for us to improve?"
                ),
                // should ask for feedback now
            },
            postMessage("Yes, actually, I'm glad you asked!"),
            postMessage("I think it's outrageous that you ask for all my personal information!"),
            postMessage("I will be sure to take this to your manager!"),
            {
                // Only type — do not submit: this simulates the user still composing in the
                // multi-line step so the chatbot keeps waiting instead of advancing.
                trigger,
                run: "edit I want to say...",
            },
            {
                // Simulate that the user is typing, so the chatbot shouldn't go to the next step
                trigger,
                async run({ edit }) {
                    chatbotDelayProcessingDef = Promise.withResolvers();
                    let failTimeout = setTimeout(() => {
                        chatbotDelayProcessingDef.reject(
                            "Chatbot should stay in multi line step when user is typing."
                        );
                    }, 5000);
                    chatbotDelayProcessingDef.promise.then(() => clearTimeout(failTimeout));
                    await edit("Never mind!");
                    await chatbotDelayProcessingDef.promise;
                    chatbotDelayProcessingDef = Promise.withResolvers();
                    failTimeout = setTimeout(() => {
                        chatbotDelayProcessingDef.reject(
                            "Chatbot should stay in multi line step if user isn't done typing."
                        );
                    }, 5000);
                    chatbotDelayProcessingDef.promise.then(() => clearTimeout(failTimeout));
                    await edit("Never mind!!!");
                    await chatbotDelayProcessingDef.promise;
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
            postMessage("no"),
            {
                trigger: messagesContain(
                    "Great, do you want to leave any feedback for us to improve?"
                ),
            },
            postMessage("no, nothing so say"),
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
