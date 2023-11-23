odoo.define('website_livechat.tour_common', function (require) {
'use strict';

// Due to some issue with assets bundles, the current file can be loaded while
// LivechatButtonView isn't, causing the patch to fail as the original model was
// not registered beforehand. The following import is intended to stop the
// execution of this file if @im_livechat/public_models/livechat_button_view is
// not part of the current assets bundles (as trying to import it will silently
// crash).
require('@im_livechat/public_models/livechat_button_view');
const { registerPatch } = require('@mail/model/model_core');
const { Markup } = require('web.utils');

registerPatch({
    name: 'LivechatButtonView',
    recordMethods: {
        /**
         * Alter this method for test purposes.
         *
         * Fake the notification after sending message as bus is not available,
         * it's necessary to add the message in the chatter + in
         * livechat.messages
         *
         * Add a class to the chatter window after sendFeedback is done
         * to force the test to wait until feedback is really done
         * (to check afterwards if the livechat session is set to inactive)
         *
         * Note : this asset is loaded for tests only (rpc call done only during
         * tests)
         *
         * @override
         */
        async sendMessage(message) {
            await this._super(message);
            if (message.isFeedback) {
                $('div.o_thread_window_header').addClass('feedback_sent');
            } else {
                this.messaging.rpc({ route: '/bus/test_mode_activated' }).then(in_test_mode => {
                    if (!in_test_mode) {
                        return;
                    }
                    this.messaging.publicLivechatGlobal.notificationHandler._handleNotification({
                        type: 'mail.channel/new_message',
                        payload: {
                            id: this.messaging.publicLivechatGlobal.publicLivechat.id,
                            message: {
                                id: this.messaging.publicLivechatGlobal.messages.length + 1,
                                author_id: [0, 'Website Visitor Test'],
                                email_from: 'Website Visitor Test',
                                body: Markup('<p>' + message.content + '</p>'),
                                is_discussion: true,
                                subtype_id: [1, "Discussions"],
                                date: moment().format('YYYY-MM-DD HH:mm:ss'),
                            },
                        },
                    });
                });
            }
        },
    },
});

/*******************************
*         Common Steps
*******************************/

var startStep = [{
    content: "click on livechat widget",
    trigger: "div.o_livechat_button"
}, {
    content: "Say hello!",
    trigger: "input.o_composer_text_field",
    run: "text Hello Sir!"
}, {
    content: "Send the message",
    trigger: "input.o_composer_text_field",
    run: function() {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    content: "Verify your message has been typed",
    trigger: "div.o_thread_message_content>p:contains('Hello Sir!')"
}, {
    content: "Verify there is no duplicates",
    trigger: "body",
    run: function () {
        if ($("div.o_thread_message_content p:contains('Hello Sir!')").length === 1) {
            $('body').addClass('no_duplicated_message');
        }
    }
}, {
    content: "Is your message correctly sent ?",
    trigger: 'body.no_duplicated_message'
}];

var endDiscussionStep = [{
    content: "Close the chatter",
    trigger: "a.o_thread_window_close",
    run: function() {
        $('a.o_thread_window_close').click();
    }
}];

var feedbackStep = [{
    content: "Type a feedback",
    trigger: "div.o_livechat_rating_reason > textarea",
    run: "text ;-) This was really helpful. Thanks ;-)!"
}, {
    content: "Send the feedback",
    trigger: "input[type='button'].o_rating_submit_button",
}, {
    content: "Check if feedback has been sent",
    trigger: "div.o_thread_window_header.feedback_sent",
}, {
    content: "Thanks for your feedback",
    trigger: "div.o_livechat_rating_box:has(div:contains('Thank you for your feedback'))",
}];

var transcriptStep = [{
    content: "Type your email",
    trigger: "input[id='o_email']",
    run: "text deboul@onner.com"
}, {
    content: "Send the conversation to your email address",
    trigger: "button.o_email_chat_button",
}, {
    content: "Type your email",
    trigger: "div.o_livechat_email:has(strong:contains('Conversation Sent'))",
}];

var closeStep = [{
    content: "Close the conversation with the x button",
    trigger: "a.o_thread_window_close",
},  {
    content: "Check that the chat window is closed",
    trigger: 'body',
    run: function () {
        if ($('div.o_livechat_button').length === 1 && !$('div.o_livechat_button').is(':visible')) {
            $('body').addClass('tour_success');
        }
    }
}, {
    content: "Is the Test succeded ?",
    trigger: 'body.tour_success'
}];

var goodRatingStep = [{
    content: "Send Good Rating",
    trigger: "div.o_livechat_rating_choices > img[data-value=5]",
}, {
    content: "Check if feedback has been sent",
    trigger: "div.o_thread_window_header.feedback_sent",
}, {
    content: "Thanks for your feedback",
    trigger: "div.o_livechat_rating_box:has(div:contains('Thank you for your feedback'))"
}];

var okRatingStep = [{
    content: "Send ok Rating",
    trigger: "div.o_livechat_rating_choices > img[data-value=3]",
}];

var sadRatingStep = [{
    content: "Send bad Rating",
    trigger: "div.o_livechat_rating_choices > img[data-value=1]",
}];

return {
    'startStep': startStep,
    'endDiscussionStep': endDiscussionStep,
    'transcriptStep': transcriptStep,
    'feedbackStep': feedbackStep,
    'closeStep': closeStep,
    'goodRatingStep': goodRatingStep,
    'okRatingStep': okRatingStep,
    'sadRatingStep': sadRatingStep,
};

});
