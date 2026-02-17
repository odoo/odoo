import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("mark-all-read", {
    condition: ({ owner, thread }) =>
        thread?.id === "inbox" && !owner.isDiscussSidebarChannelActions,
    disabledCondition: ({ thread }) => thread.isEmpty,
    onSelected: ({ store }) =>
        store.env.services.orm.silent.call("mail.message", "mark_all_as_read"),
    sequence: 1,
    name: _t("Mark all read"),
});
registerThreadAction("remove-all-bookmarks", {
    condition: ({ owner, store, thread }) =>
        thread?.eq(store.bookmarkBox) && !owner.isDiscussSidebarChannelActions,
    disabledCondition: ({ thread }) => thread.isEmpty,
    onSelected: ({ store }) => store.removeAllBookmarks(),
    sequence: 2,
    name: _t("Remove all bookmarks"),
});
