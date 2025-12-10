import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("im_livechat.looking_for_help_discuss_category_tour", {
    steps: () => [
        {
            // Two live chats are looking for help, they are both in the "Looking for help" category.
            trigger:
                ".o-mail-DiscussSidebarCategory-livechatNeedHelp + .o-mail-DiscussSidebarChannel-container:contains(Visitor Accounting) + .o-mail-DiscussSidebarChannel-container:contains(Visitor Sales)",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Sales) .o-mail-starred",
        },
        {
            trigger:
                ".o-mail-DiscussSidebarChannel:contains(Accounting):not(:has(.o-mail-starred))",
        },
        {
            trigger: ".o-mail-DiscussSidebarChannel:contains(Accounting)",
            run: "hover && click [title='Chat Actions']",
        },
        {
            trigger:
                ".o-mail-DiscussSidebar:has(.o-mail-DiscussSidebarChannel:contains(Accounting))",
        },
        {
            trigger: "button[name='livechat-status']",
            run: "hover",
        },
        {
            trigger: ".o-livechat-LivechatStatusSelection-Label:contains(In progress)",
            run: "click",
        },
        {
            trigger:
                ".o-mail-DiscussSidebar:not(:has(.o-mail-DiscussSidebarChannel:contains(Accounting)))",
        },
    ],
});
