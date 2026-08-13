import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";

registry.category("web_tour.tours").add("discuss_channel_tour", {
    url: "/odoo",
    steps: () => [
        {
            isActive: ["enterprise"],
            trigger: "a[data-menu-xmlid='mail.menu_root_discuss']",
            content: _t("Open Discuss App"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSidebarCategory-channel .o-mail-DiscussSidebarCategory-add",
            content: markup(
                _t(
                    "<p>Channels make it easy to organize information across different topics and groups.</p> <p>Try to <b>create your first channel</b> (e.g. sales, marketing, product XYZ, after work party, etc).</p>"
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-discuss-ChannelSelector input",
            content: markup(_t("<p>Create a channel here.</p>")),
            tooltipPosition: "bottom",
            run: `edit SomeChannel_${new Date().getTime()}`,
        },
        {
            trigger: ".o-discuss-ChannelSelector-suggestion",
            content: markup(_t("<p>Create a public or private channel.</p>")),
            run: "click",
            tooltipPosition: "right",
        },
        {
            trigger: ".o-mail-Composer-input",
            content: markup(
                _t(
                    "<p><b>Write a message</b> to the members of the channel here.</p> <p>You can notify someone with <i>'@'</i> or link another channel with <i>'#'</i>. Start your message with <i>'/'</i> to get the list of possible commands.</p>"
                )
            ),
            tooltipPosition: "top",
            run: `edit SomeText_${new Date().getTime()}`,
        },
        {
            trigger: ".o-mail-Composer-send:enabled",
            content: _t("Post your message on the thread"),
            tooltipPosition: "top",
            run: "click",
        },
        {
            trigger: ".o-mail-Message[data-persistent]:contains(today at)",
            content: _t("Hover on your message and mark as todo"),
            tooltipPosition: "top",
            run: "hover && click .o-mail-Message [title='Mark as Todo']",
        },
        {
            trigger: "button:contains(Starred)",
            content: _t(
                "Once a message has been starred, you can come back and review it at any time here."
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSidebarCategory-chat .o-mail-DiscussSidebarCategory-add",
            content: markup(
                _t(
                    "<p><b>Chat with coworkers</b> in real-time using direct messages.</p><p><i>You might need to invite users from the Settings app first.</i></p>"
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-discuss-ChannelSelector",
        },
    ],
});
