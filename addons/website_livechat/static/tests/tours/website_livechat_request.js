odoo.define('website_livechat.chat_request_tour', function(require) {
'use strict';

var commonSteps = require("website_livechat.tour_common");
var tour = require("web_tour.tour");


var stepWithChatRequestStep = [{
    content: "Answer the chat request!",
    trigger: "input.o_composer_text_field",
    run: "text Hi ! What a coincidence! I need your help indeed."
}, {
    content: "Send the message",
    trigger: "input.o_composer_text_field",
    run: function() {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    content: "Verify your message has been typed",
    trigger: "div.o_thread_message_content>p:contains('Hi ! What a coincidence! I need your help indeed.')"
}, {
    content: "Verify there is no duplicates",
    trigger: "body",
    run: function () {
        if ($("div.o_thread_message_content p:contains('Hi ! What a coincidence! I need your help indeed.')").length === 1) {
            $('body').addClass('no_duplicated_message');
        }
    }
}, {
    content: "Is your message correctly sent ?",
    trigger: 'body.no_duplicated_message'
}];


tour.register('website_livechat_chat_request_part_1_no_close_tour', {
    test: true,
    url: '/',
}, [].concat(stepWithChatRequestStep));

tour.register('website_livechat_chat_request_part_2_end_session_tour', {
    test: true,
    url: '/',
}, [].concat(commonSteps.endDiscussionStep, commonSteps.okRatingStep, commonSteps.feedbackStep, commonSteps.transcriptStep, commonSteps.closeStep));

return {};
});
