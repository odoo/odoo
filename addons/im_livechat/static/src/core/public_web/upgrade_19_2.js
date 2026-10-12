import { upgrade_19_2 } from "@mail/core/common/upgrade/upgrade_19_2";

upgrade_19_2.add("DiscussApp,undefined:isLivechatInfoPanelOpenByDefault", ({ value }) => ({
    key: "DiscussApp:isLivechatInfoPanelOpenByDefault",
    value: upgrade_19_2.parseRawValue(value).value,
}));
