import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat.meeting_view_tour", {
    steps: () => [
        {
            trigger: ".o-livechat-root:shadow .o-livechat-LivechatButton",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Thread[data-transient]",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "edit Hello!",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Composer-input",
            run: "press Enter",
        },
        {
            trigger: ".o-livechat-root:shadow [title='Join Call']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-discuss-Call [title='Fullscreen']",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-Meeting",
        },
        {
            trigger: ".o-livechat-root:shadow .o-mail-MeetingSideActions [name^='more-action:'] ",
            run: "click",
        },
        {
            trigger: ".o-livechat-root:shadow [name='call-settings']",
            run: "click",
        },
        {
            trigger:
                ".o-livechat-root:shadow .o-mail-DiscussContent-panelContainer .o-mail-ActionPanel-header:contains('voice settings')",
        },
    ],
});
