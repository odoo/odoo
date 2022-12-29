/** @odoo-module **/

import { _t } from "web.core";
import { Markup } from "web.utils";
import tour from "web_tour.tour";

tour.register(
    "mail_tour",
    {
        url: "/web#action=mail.action_discuss",
        sequence: 80,
    },
    [
        {
            trigger: ".o-mail-category-channel .o-mail-category-add-button",
            content: Markup(
                _t(
                    "<p>Channels make it easy to organize information across different topics and groups.</p> <p>Try to <b>create your first channel</b> (e.g. sales, marketing, product XYZ, after work party, etc).</p>"
                )
            ),
            position: "bottom",
        },
        {
            trigger: ".o-mail-channel-selector .o_input",
            content: Markup(_t("<p>Create a channel here.</p>")),
            position: "bottom",
            auto: true,
            run: function (actions) {
                var t = new Date().getTime();
                actions.text("SomeChannel_" + t, this.$anchor);
            },
        },
        {
            trigger: ".o-mail-channel-selector .o-autocomplete--dropdown-menu",
            content: Markup(_t("<p>Create a public or private channel.</p>")),
            position: "right",
            run() {
                this.$consumeEventAnchors.find("li:first").click();
            },
        },
        {
            trigger: ".o-mail-composer-textarea",
            content: Markup(
                _t(
                    "<p><b>Write a message</b> to the members of the channel here.</p> <p>You can notify someone with <i>'@'</i> or link another channel with <i>'#'</i>. Start your message with <i>'/'</i> to get the list of possible commands.</p>"
                )
            ),
            position: "top",
            width: 350,
            run: function (actions) {
                var t = new Date().getTime();
                actions.text("SomeText_" + t, this.$anchor);
            },
        },
        {
            trigger: ".o-mail-composer-send-button",
            content: _t("Post your message on the thread"),
            position: "top",
        },
        {
            trigger: ".o-mail-message",
            content: _t("Click on your message"),
            position: "top",
        },
        // TODO race condition to fix here, clicking on star while the message is still pending leads to a crash
        {
            trigger: ".o-mail-message-toggle-star",
            content: Markup(
                _t("Messages can be <b>starred</b> to remind you to check back later.")
            ),
            position: "bottom",
        },
        {
            trigger: ".o-starred-box",
            content: _t(
                "Once a message has been starred, you can come back and review it at any time here."
            ),
            position: "bottom",
        },
        {
            trigger: ".o-mail-category-chat .o-mail-category-add-button",
            content: Markup(
                _t(
                    "<p><b>Chat with coworkers</b> in real-time using direct messages.</p><p><i>You might need to invite users from the Settings app first.</i></p>"
                )
            ),
            position: "bottom",
        },
    ]
);
