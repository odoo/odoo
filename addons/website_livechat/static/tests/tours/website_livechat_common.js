/** @odoo-module alias=website_livechat.tour_common **/

import { patch } from "@web/core/utils/patch";
import { LivechatService } from "@im_livechat/new/core/livechat_service";
import { RATING } from "@im_livechat/new/feedback_panel/feedback_panel";

patch(LivechatService.prototype, "website_livechat", {
    sendFeedback() {
        document.body.classList.add("feedback_sent");
        return this._super(...arguments);
    },
});

/*******************************
*         Common Steps
*******************************/

var startStep = [{
    content: "click on livechat widget",
    trigger: ".o-livechat-LivechatButton",
}, {
    content: "Say hello!",
    trigger: ".o-mail-Composer-input",
    run: "text Hello Sir!"
}, {
    content: "Send the message",
    trigger: ".o-mail-Composer-input",
    run() {
        this.$anchor[0].dispatchEvent(
            new KeyboardEvent("keydown", { key: "Enter", which: 13, bubbles: true })
        );
    },
}, {
    content: "Verify your message has been typed",
    trigger: ".o-mail-Message:contains('Hello Sir!')"
}, {
    content: "Verify there is no duplicates",
    trigger: ".o-mail-Thread",
    run() {
        if (this.$anchor.find(".o-mail-Message:contains('Hello Sir!')").length === 1) {
            $('body').addClass('no_duplicated_message');
        }
    },
}, {
    content: "Is your message correctly sent ?",
    trigger: 'body.no_duplicated_message',
    shadowDOM: false,
}];

var endDiscussionStep = [{
    content: "Close the chat window",
    trigger: ".o-mail-ChatWindow-command[title*=Close]",
    run: "click",
}];

var feedbackStep = [{
    content: "Type a feedback",
    trigger: "textarea[placeholder='Explain your note']",
    run: "text ;-) This was really helpful. Thanks ;-)!"
}, {
    content: "Send the feedback",
    trigger: "button:contains(Send)",
}, {
    content: "Check if feedback has been sent",
    trigger: "body.feedback_sent",
    shadowDOM: false,
}, {
    content: "Thanks for your feedback",
    trigger: "p:contains('Thank you for your feedback')",
}];

var transcriptStep = [{
    content: "Type your email",
    trigger: "input[placeholder='mail@example.com']",
    run: "text deboul@onner.com"
}, {
    content: "Send the conversation to your email address",
    trigger: "button[data-action=sendTranscript]",
}, {
    content: "Check conversation is sent",
    trigger: ".form-text:contains(The conversation was sent)",
}];

var closeStep = [{
    content: "Close the conversation with the x button",
    trigger: ".o-mail-ChatWindow-command[title*=Close]",
    run: "click",
},  {
    content: "Check that the button is not displayed anymore",
    trigger: '.o-mail-ChatWindowContainer',
    allowInvisible: true,
    run() {
        if (this.$anchor.find('.o-livechat-livechatButton').length === 0) {
            $('body').addClass('tour_success');
        }
    },
}, {
    content: "Is the Test succeded ?",
    trigger: 'body.tour_success',
    shadowDOM: false,
}];

var goodRatingStep = [{
    content: "Choose Good Rating",
    trigger: `img[src*=rating][alt=${RATING.GOOD}]`,
}];

var okRatingStep = [{
    content: "Choose ok Rating",
    trigger: `img[src*=rating][alt=${RATING.OK}]`,
}];

var sadRatingStep = [{
    content: "Choose bad Rating",
    trigger: `img[src*=rating][alt=${RATING.BAD}]`,
}];

export default {
    'startStep': startStep,
    'endDiscussionStep': endDiscussionStep,
    'transcriptStep': transcriptStep,
    'feedbackStep': feedbackStep,
    'closeStep': closeStep,
    'goodRatingStep': goodRatingStep,
    'okRatingStep': okRatingStep,
    'sadRatingStep': sadRatingStep,
};
