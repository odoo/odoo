/** @odoo-module */

import tour from "web_tour.tour";

import { patchRecordMethods } from '@mail/model/model_core';
// ensure that the model definition is loaded before the patch
import '@im_livechat/models/livechat_button_view';

patchRecordMethods('LivechatButtonView', {
    /**
     * Let us make it a bit faster than the default delay (3500ms).
     * Let us also debounce waiting for more user inputs for only 500ms.
     */
    start() {
        this.messaging.publicLivechatGlobal.chatbot.update({ isWebsiteLivechatTourFlow: true });
        this._super();
    },
});


const messagesContain = (text) => `div.o_thread_message_content:contains("${text}")`;

tour.register('website_livechat_chatbot_flow_tour', {
    test: true,
    url: '/',
}, [{
    trigger: messagesContain("Hello! I'm a bot!"),
    run: () => {}  // check first welcome message is posted
}, {
    trigger: messagesContain("I help lost visitors find their way."),
    run: () => {}  // check second welcome message is posted
}, {
    trigger: messagesContain("How can I help you?"),
    run: () => {}  // check question_selection message is posted
}, {
    trigger: '.o_livechat_chatbot_options li:contains("I want to buy the software")',
    run: 'click'
}, {
    trigger: messagesContain("I want to buy the software"),
    run: () => {}  // check selected option is posted
}, {
    trigger: messagesContain("Can you give us your email please?"),
    run: () => {}  // check ask email step following selecting option A
}, {
    trigger: "input.o_composer_text_field",
    run: "text No, you won't get my email!"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: messagesContain("'No, you won't get my email!' does not look like a valid email. Can you please try again?"),
    run: () => {}  // check invalid email detected and the bot asks for a retry
}, {
    trigger: "input.o_composer_text_field",
    run: "text okfine@fakeemail.com"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: messagesContain("Your email is validated, thank you!"),
    run: () => {}  // check that this time the email goes through and we proceed to next step
}, {
    trigger: messagesContain("Would you mind providing your website address?"),
    run: () => {}  // should ask for website now
}, {
    trigger: "input.o_composer_text_field",
    run: "text https://www.fakeaddress.com"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: messagesContain("Great, do you want to leave any feedback for us to improve?"),
    run: () => {}  // should ask for feedback now
}, {
    trigger: "input.o_composer_text_field",
    run: "text Yes, actually, I'm glad you asked!"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: "input.o_composer_text_field",
    run: "text I think it's outrageous that you ask for all my personal information!"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: "input.o_composer_text_field",
    run: "text I will be sure to take this to your manager!"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: messagesContain("Ok bye!"),
    run: () => {}  // last step is displayed
}, {
    trigger: '.o_livechat_chatbot_restart',
    run: 'click'
}, {
    trigger: messagesContain("Restarting conversation..."),
    run: () => {}  // check that conversation is properly restarting
}, {
    trigger: messagesContain("Hello! I'm a bot!"),
    run: () => {}  // check first welcome message is posted
}, {
    trigger: messagesContain("I help lost visitors find their way."),
    run: () => {}  // check second welcome message is posted
}, {
    trigger: messagesContain("How can I help you?"),
    run: () => {}  // check question_selection message is posted
}, {
    trigger: '.o_livechat_chatbot_options li:contains("Pricing Question")',
    run: 'click'
}, {
    trigger: messagesContain("For any pricing question, feel free ton contact us at pricing@mycompany.com"),
    run: () => {}  // the path should now go towards 'Pricing Question (first part)'
}, {
    trigger: messagesContain("We will reach back to you as soon as we can!"),
    run: () => {}  // the path should now go towards 'Pricing Question (second part)'
}, {
    trigger: messagesContain("Would you mind providing your website address?"),
    run: () => {}  // should ask for website now
}, {
    trigger: "input.o_composer_text_field",
    run: "text no"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: messagesContain("Great, do you want to leave any feedback for us to improve?"),
    run: () => {}  // should ask for feedback now
}, {
    trigger: "input.o_composer_text_field",
    run: "text no, nothing so say"
}, {
    trigger: "input.o_composer_text_field",
    run: () => {
        $('input.o_composer_text_field').trigger($.Event('keydown', {which: $.ui.keyCode.ENTER}));
    }
}, {
    trigger: messagesContain("Ok bye!"),
    run: () => {}  // last step is displayed
}]);
