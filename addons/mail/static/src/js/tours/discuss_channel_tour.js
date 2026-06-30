import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { markup } from "@odoo/owl";
import { delay } from "@web/core/utils/concurrency";

registry.category("web_tour.tours").add("discuss_channel_tour", {
    steps: () => [
        {
            isActive: ["enterprise"],
            trigger: "a[data-menu-xmlid='mail.menu_root_discuss']",
            content: _t("Open Discuss App"),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-mail-MessagingMenu-tab:has(:text('Channels'))",
            content: markup(
                _t(
                    "<p>Channels make it easy to organize information across different topics and groups.</p>"
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger:
                ".o-mail-Discuss:has(.o-mail-MessagingMenu-tab:has(:text('Channels')).active) .o-mail-NotificationItem:eq(0)",
            content: markup(_t("<p>Click a channel to open the discussion.</p>")),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-mail-Composer-input",
            content: markup(
                _t(
                    "<p><b>Write a message</b> to the members of the channel here.</p> <p>You can notify someone with <i>'@'</i>. Start your message with <i>'/'</i> to get the list of possible commands.</p>"
                )
            ),
            tooltipPosition: "top",
            run: `edit SomeText_${new Date().getTime()}`,
        },
        {
            trigger: ".o-mail-Composer-input",
            content: _t("Post your message on the thread"),
            tooltipPosition: "top",
            run: "press Enter",
        },
        {
            trigger:
                ".o-mail-Message[data-persistent] [name='more-action:undefined']:not(:visible)",
            content: _t("Hover and click to view more actions on the message"),
            tooltipPosition: "top",
            async run(helpers) {
                await delay(1000);
                await helpers.click();
            },
        },
        {
            trigger: ".o-dropdown-item[name='add-bookmark']",
            content: _t("click to bookmark your message"),
            tooltipPosition: "right",
            run: "click",
        },
        {
            trigger: ".o-mail-MessagingMenu-tab:has(:text('Bookmarks))",
            content: _t(
                "Once a message has been bookmarked, you can come back and review it at any time here."
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSearch-inputContainer",
            content: markup(
                _t(
                    "<p><b>Chat with coworkers</b> in real-time using direct messages.</p><p><i>You might need to invite users from the Settings app first.</i></p>"
                )
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});
