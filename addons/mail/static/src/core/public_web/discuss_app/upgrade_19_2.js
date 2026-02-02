import { upgrade_19_2 } from "@mail/core/common/upgrade/upgrade_19_2";

upgrade_19_2.add(/^mail\.sidebar_category_(.*)_hidden$/, ({ matchOfKey }) => ({
    key: `DiscussAppCategory,${matchOfKey[1]}:hidden`,
    value: true,
}));

const discussAppFields = ["isMemberPanelOpenByDefault", "isSidebarCompact", "lastActiveId"];
for (const fieldName of discussAppFields) {
    upgrade_19_2.add(`DiscussApp,undefined:${fieldName}`, ({ value }) => ({
        key: `DiscussApp:${fieldName}`,
        value: upgrade_19_2.parseRawValue(value).value,
    }));
}
