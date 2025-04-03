import { markup } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

const tags = {
    b_open: markup`<b>`,
    b_close: markup`</b>`,
    i_open: markup`<i>>`,
    i_close: markup`</i>`,
    p_open: markup`<p>>`,
    p_close: markup`</p>`,
};

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
            trigger: ".o-mail-DiscussSidebarCategories-search",
            content: _t(
                "%{p_open}sChannels make it easy to organize information across different topics and groups.%{p_close}s %{p_open}sTry to %(b_open)screate your first channel%(b_close)s (e.g. sales, marketing, product XYZ, after work party, etc).%{p_close}s",
                tags
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o_command_palette_search input",
            content: _t("%{p_open}sCreate a channel here.%{p_close}s", tags),
            tooltipPosition: "bottom",
            run: `edit SomeChannel_${new Date().getTime()}`,
        },
        {
            trigger: ".o-mail-DiscussCommand-createChannel",
            content: _t("%{p_open}sCreate a public or private channel.%{p_close}s", tags),
            run: "click",
            tooltipPosition: "right",
        },
        {
            trigger: ".o-mail-Composer-input",
            content: _t(
                "%{p_open}s%{b_open}sWrite a message%(b_close)s to the members of the channel here.%{p_close}s %{p_open}sYou can notify someone with <i>'@'</i> or link another channel with <i>'#'</i>. Start your message with <i>'/'</i> to get the list of possible commands.%{p_close}s",
                tags
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
            trigger: ".o-mail-Message:contains(today at)",
            content: _t("Hover on your message and mark as todo"),
            tooltipPosition: "top",
            run: "hover && click .o-mail-Message [title='Mark as Todo']",
        },
        {
            trigger: "button[data-mailbox-id='starred']",
            content: _t(
                "Once a message has been starred, you can come back and review it at any time here."
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
        {
            trigger: ".o-mail-DiscussSidebarCategories-search",
            content: _t(
                "%{p_open}s%{b_open}sChat with coworkers%(b_close)s in real-time using direct messages.%{p_close}s%{p_open}s%{i_open}sYou might need to invite users from the Settings app first.%{i_close}s%{p_close}s",
                tags
            ),
            tooltipPosition: "bottom",
            run: "click",
        },
    ],
});
