/** @odoo-module **/

import { _t } from 'web.core';
import { Markup } from 'web.utils';
import tour from 'web_tour.tour';

tour.register('mail_tour', {
    url: "/web#action=mail.widgets.discuss",
    sequence: 80,
}, [{
    trigger: '.o_DiscussSidebar_categoryChannel .o_DiscussSidebarCategory_commandAdd',
    content: Markup(_t("<p>Channels make it easy to organize information across different topics and groups.</p> <p>Try to <b>create your first channel</b> (e.g. sales, marketing, product XYZ, after work party, etc).</p>")),
    position: 'bottom',
}, {
    trigger: '.o_DiscussSidebarCategory_itemNewInput',
    content: Markup(_t("<p>Create a channel here.</p>")),
    position: 'bottom',
    auto: true,
    run: function (actions) {
        var t = new Date().getTime();
        actions.text("SomeChannel_" + t, this.$anchor);
    },
}, {
    trigger: ".o_DiscussSidebarCategory_newChannelAutocompleteSuggestions",
    content: Markup(_t("<p>Create a public or private channel.</p>")),
    position: 'right',
    run() {
        this.$consumeEventAnchors.find('li:first').click();
    },
}, {
    trigger: '.o_Discuss_thread .o_ComposerTextInput_textarea',
    content: Markup(_t("<p><b>Write a message</b> to the members of the channel here.</p> <p>You can notify someone with <i>'@'</i> or link another channel with <i>'#'</i>. Start your message with <i>'/'</i> to get the list of possible commands.</p>")),
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
    trigger: '.o_Discuss_thread .o_Message',
    content: _t("Click on your message"),
    position: "top",
}, {
    trigger: '.o_Discuss_thread .o_MessageActionList_actionStar',
    content: Markup(_t("Messages can be <b>starred</b> to remind you to check back later.")),
    position: "bottom",
}, {
    trigger: '.o_DiscussSidebarMailbox.o-starred-box',
    content: _t("Once a message has been starred, you can come back and review it at any time here."),
    position: "bottom",
}, {
    trigger: '.o_DiscussSidebar_categoryChat .o_DiscussSidebarCategory_commandAdd',
    content: Markup(_t("<p><b>Chat with coworkers</b> in real-time using direct messages.</p><p><i>You might need to invite users from the Settings app first.</i></p>")),
    position: 'bottom',
}]);
