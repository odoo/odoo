import { registerThreadAction } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";
import { ACTION_TAGS } from "@mail/core/common/action";

registerThreadAction("leave", {
    condition: ({ owner, thread }) =>
        (thread?.canLeave || thread?.canUnpin) && !owner.isDiscussContent,
    icon: "fa fa-fw fa-sign-out",
    name: ({ thread }) => (thread.canLeave ? _t("Leave Channel") : _t("Unpin Conversation")),
    open: ({ thread }) => (thread.canLeave ? thread.leaveChannel() : thread.unpin()),
    partition: ({ owner }) => owner.env.inChatWindow,
    sequence: 10,
    sequenceGroup: 40,
    tags: ACTION_TAGS.DANGER,
});
