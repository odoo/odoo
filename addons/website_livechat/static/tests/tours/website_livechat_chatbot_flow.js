import { patch } from "@web/core/utils/patch";
import { registry } from "@web/core/registry";
import { Chatbot } from "@im_livechat/core/common/chatbot_model";
import {
    editComposer,
    LIVECHAT_COMPOSER,
    postMessage,
    waitForMessage,
} from "@im_livechat/../tests/tours/livechat_tour_utils";

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
            waitForMessage("Hello! I'm a bot!"),
            waitForMessage("I help lost visitors find their way."),
            waitForMessage("How can I help you?"),
            {
                content: "Reactions should not be available before thread is persisted.",
                trigger: `body:not(:has(.o-mail-Message-actions [title='Add a Reaction']))`,
            },
            {
                trigger: '.o-livechat-root:shadow button:text("I\'d like to buy the software")',
                run: "click",
            },
            {
                // check selected option is posted and reactions are available since
                // the thread has been persisted in the process
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow .o-mail-Message:has(.o-mail-Message-actions [title='Add a Reaction']):text('I\\'d like to buy the software')",
            },
            waitForMessage("Can you give us your email please?"),
            ...postMessage("No, you won't get my email!"),
            waitForMessage(
                "'No, you won't get my email!' does not look like a valid email. Can you please try again?"
            ),
            ...postMessage("okfine@fakeemail.com"),
            waitForMessage("Your email is validated, thank you!"),
            waitForMessage("Can you give us your phone number please?"),
            ...postMessage("123456"),
            waitForMessage(
                "'123456' does not look like a valid phone number. Can you please try again?"
            ),
            ...postMessage("+919876543210"),
            waitForMessage("Your phone number is validated. thank you!"),
            waitForMessage("Would you mind providing your website address?"),
            ...postMessage("https://www.fakeaddress.com"),
            waitForMessage("Great, do you want to leave any feedback for us to improve?"),
            ...postMessage("Yes, actually, I'm glad you asked!"),
            ...postMessage("I think it's outrageous that you ask for all my personal information!"),
            ...postMessage("I will be sure to take this to your manager!"),
            // Only type, do not submit: this simulates the user still composing in the
            // multi-line step so the chatbot keeps waiting instead of advancing.
            editComposer("I want to say..."),
            {
                // Simulate that the user is typing, so the chatbot shouldn't go to the next step
                trigger: `${LIVECHAT_COMPOSER}:enabled`,
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
            waitForMessage("Ok bye!"),
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow-header [title='Restart Conversation']",
                run: "click",
            },
            waitForMessage("Restarting conversation..."),
            waitForMessage("Hello! I'm a bot!", { index: 1 }),
            waitForMessage("I help lost visitors find their way.", { index: 1 }),
            waitForMessage("How can I help you?", { index: 1 }),
            {
                trigger: '.o-livechat-root:shadow button:text("Pricing Question")',
                run: "click",
            },
            waitForMessage(
                "For any pricing question, feel free ton contact us at pricing@mycompany.com"
            ),
            waitForMessage("We will reach back to you as soon as we can!"),
            waitForMessage("Would you mind providing your website address?", { index: 1 }),
            ...postMessage("no"),
            waitForMessage("Great, do you want to leave any feedback for us to improve?", {
                index: 1,
            }),
            ...postMessage("no, nothing so say"),
            waitForMessage("Ok bye!", { index: 1 }),
            {
                trigger:
                    ".o-livechat-root:shadow .o-mail-ChatWindow-header [title='Restart Conversation']",
                run: "click",
            },
            {
                trigger: ".o-livechat-root:shadow button:text(I want to speak with an operator)",
                run: "click",
            },
            waitForMessage("I will transfer you to a human."),
            {
                // Wait for the operator to be added: composer is only enabled at that point.
                trigger: ".o-livechat-root:shadow .o-mail-Composer-html:enabled",
            },
        ];
    },
});
