import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("mark-all-read", {
    condition: ({ owner, thread }) =>
        thread?.id === "inbox" && !owner.isDiscussSidebarChannelActions,
    disabledCondition: ({ thread }) => thread.isEmpty,
    onSelected: async ({ store }) => {
        const orm = store.env.services.orm;
        const readMessageIds = await orm.silent.call("mail.message", "mark_all_as_read");
        const closeFn = store.env.services.notification.add(_t("Marked as read"), {
            type: "success",
            buttons: [
                {
                    name: _t("Undo"),
                    icon: "fa-undo",
                    onClick: () => {
                        orm.silent.call("mail.message", "mark_as_unread", [readMessageIds]);
                        closeFn();
                    },
                },
            ],
        });
    },
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
