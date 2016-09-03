odoo.define('mail.tour', function(require) {
"use strict";

var core = require('web.core');
var tour = require('web_tour.tour');

var _t = core._t;

tour.register('mail_tour', [{
    trigger: '.o_mail_chat .o_mail_chat_sidebar .o_add[data-type="public"]',
    content: _t("<p>Channels make it easy to organize information across different topics and groups.</p> <p>Try to <b>create your first channel</b> (e.g. sales, marketing, product XYZ, after work party, etc).</p>"),
    position: 'bottom',
}, {
    trigger: '.o_mail_chat .o_composer_text_field',
    content: _t("<p><b>Write a message</b> to the members of the channel here.</p> <p>You can notify someone with <i>\'@\'</i> or link another channel with <i>\'#\'</i>. Start your message with <i>\'/\'</i> to get the list of possible commands.</p>"),
    position: "top",
    width: 350,
}, {
    trigger: ".o_mail_chat .o_mail_thread .o_thread_message_star",
    content: _t("Messages can be <b>starred</b> to remind you to check back later."),
    position: "right",
}, {
    trigger: '.o_mail_chat .o_mail_chat_channel_item[data-channel-id="channel_starred"]',
    content: _t("Once a message has been starred, you can come back and review it at any time here."),
    position: "bottom",
}, {
    trigger: '.o_mail_chat .o_mail_chat_sidebar .o_add[data-type="dm"]',
    content: _t("<p><b>Chat with coworkers</b> in real-time using direct messages.</p><p><i>You might need to invite users from the Settings app first.</i></p>"),
    position: 'bottom',
}]);

});
