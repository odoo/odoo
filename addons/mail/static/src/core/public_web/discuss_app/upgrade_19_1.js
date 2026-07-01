import { upgrade_19_1 } from "@mail/core/common/upgrade/upgrade_19_1";

upgrade_19_1.add("mail.user_setting.no_members_default_open", {
    key: "DiscussApp,undefined:isMemberPanelOpenByDefault",
    value: false,
});

upgrade_19_1.add("mail.user_setting.discuss_sidebar_compact", {
    key: "DiscussApp,undefined:isSidebarCompact",
    value: true,
});

upgrade_19_1.add("mail.user_setting.discuss_last_active_id", ({ value }) => ({
    key: "DiscussApp,undefined:lastActiveId",
    value,
}));
