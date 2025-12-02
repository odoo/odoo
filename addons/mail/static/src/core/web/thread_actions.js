import { registerThreadAction } from "@mail/core/common/thread_actions";

import { _t } from "@web/core/l10n/translation";

registerThreadAction("mark-all-read", {
    condition: ({ owner, thread }) =>
        thread?.id === "inbox" && !owner.isDiscussSidebarChannelActions,
    disabledCondition: ({ thread }) => thread.isEmpty,
    open: ({ store }) => store.env.services.orm.silent.call("mail.message", "mark_all_as_read"),
    sequence: 1,
    name: _t("Mark all read"),
});
registerThreadAction("unstar-all", {
    condition: ({ owner, thread }) =>
        thread?.id === "starred" && !owner.isDiscussSidebarChannelActions,
    disabledCondition: ({ thread }) => thread.isEmpty,
    open: ({ store }) => store.unstarAll(),
    sequence: 2,
    name: _t("Unstar all"),
});
