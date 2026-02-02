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
registerThreadAction("unstar-all", {
    condition: ({ owner, thread }) =>
        thread?.id === "starred" && !owner.isDiscussSidebarChannelActions,
    disabledCondition: ({ thread }) => thread.isEmpty,
    onSelected: ({ store }) => store.unstarAll(),
    sequence: 2,
    name: _t("Unstar all"),
});
registerThreadAction("inbox-filters", {
    condition: ({ owner, store, thread }) =>
        store.self_user?.notification_type === "inbox" &&
        thread?.model === "mail.box" &&
        !owner.isDiscussSidebarChannelActions,
    dropdown: true,
    dropdownTemplate: "mail.MailboxesSelection",
    dropdownPosition: "bottom-end",
    sequence: 10,
    sequenceGroup: 20,
    icon: "fa fa-fw fa-filter",
    name: _t("Change Mailbox"),
});
