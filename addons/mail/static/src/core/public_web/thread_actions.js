import { threadActionsRegistry } from "@mail/core/common/thread_actions";
import { _t } from "@web/core/l10n/translation";

threadActionsRegistry
    .add("leave", {
        condition: (component) => component.thread?.canLeave,
        icon: "fa fa-fw fa-sign-out text-danger",
        iconLarge: "fa fa-fw fa-lg fa-sign-out text-danger",
        name: _t("Leave Channel"),
        nameClass: "text-danger",
        open: (component) => component.thread.leaveChannel(),
        partition: (component) => component.env.inChatWindow,
        sequence: 10,
        sequenceGroup: 40,
        sidebarSequence: 10,
        sidebarSequenceGroup: 40,
    })
    .add("unpin", {
        condition: (component) => component.thread?.canUnpin,
        icon: "fa fa-fw fa-thumb-tack text-danger",
        iconLarge: "fa fa-fw fa-lg fa-thumb-tack text-danger",
        name: _t("Unpin Conversation"),
        nameClass: "text-danger",
        open: (component) => component.thread.unpin(),
        partition: (component) => component.env.inChatWindow,
        sequence: 20,
        sequenceGroup: 40,
        sidebarSequence: 20,
        sidebarSequenceGroup: 40,
    });
