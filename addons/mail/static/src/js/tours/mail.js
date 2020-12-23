odoo.define('mail.tour', function (require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('mail_tour', {
    url: "/web#action=mail.widgets.discuss",
}, [{
    trigger: '.o_DiscussSidebar_groupChannel .o_DiscussSidebar_groupHeaderItemAdd',
    content: _t("<p>Channels make it easy to organize information across different topics and groups.</p> <p>Try to <b>create your first channel</b> (e.g. sales, marketing, product XYZ, after work party, etc).</p>"),
    position: 'bottom',
}, {
    trigger: '.o_DiscussSidebar_itemNewInput',
    content: _t("<p>Create a channel here.</p>"),
    position: 'bottom',
    auto: true,
    run: function (actions) {
        var t = new Date().getTime();
        actions.text("SomeChannel_" + t, this.$anchor);
    },
}, {
    trigger: ".o_DiscussSidebar_newChannelAutocompleteSuggestions",
    content: _t("<p>Create a public or private channel.</p>"),
    position: 'right',
    run() {
        this.$consumeEventAnchors.find('li:first').click();
    },
}, {
    trigger: '.o_Discuss_thread .o_ComposerTextInput_textarea',
    content: _t("<p><b>Write a message</b> to the members of the channel here.</p> <p>You can notify someone with <i>'@'</i> or link another channel with <i>'#'</i>. Start your message with <i>'/'</i> to get the list of possible commands.</p>"),
    position: "top",
    width: 350,
    run: function (actions) {
        var t = new Date().getTime();
        actions.text("SomeText_" + t, this.$anchor);
    },
}, {
    trigger: '.o_Discuss_thread .o_Composer_buttonSend',
    content: _t("Post your message on the thread"),
    position: "top",
}, {
    trigger: '.o_Discuss_thread .o_Message_commandStar',
    content: _t("Messages can be <b>starred</b> to remind you to check back later."),
    position: "bottom",
}, {
    trigger: '.o_DiscussSidebarItem.o-starred-box',
    content: _t("Once a message has been starred, you can come back and review it at any time here."),
    position: "bottom",
}, {
    trigger: '.o_DiscussSidebar_groupChat .o_DiscussSidebar_groupHeaderItemAdd',
    content: _t("<p><b>Chat with coworkers</b> in real-time using direct messages.</p><p><i>You might need to invite users from the Settings app first.</i></p>"),
    position: 'bottom',
}]);

});
