import { useSubEnv } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { MeetingChat } from "@mail/discuss/call/common/meeting_chat";

export const threadActionsRegistry = registry.category("mail.thread/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").Thread} Thread */

/**
 * @typedef {ActionDefinition} ThreadActionDefinition
 */

/**
 * @param {string} id
 * @param {ThreadActionDefinition} definition
 */
export function registerThreadAction(id, definition) {
    threadActionsRegistry.add(id, definition);
}

registerThreadAction("fold-chat-window", {
    condition: ({ owner }) => owner.props.chatWindow && !owner.isDiscussSidebarChannelActions,
    icon: "oi oi-fw oi-minus",
    name: ({ owner }) => (!owner.props.chatWindow?.isOpen ? _t("Open") : _t("Fold")),
    onSelected: ({ owner }) => owner.toggleFold(),
    displayActive: ({ owner }) => !owner.props.chatWindow?.isOpen,
    sequence: 99,
    sequenceQuick: 20,
});
registerThreadAction("rename-thread", {
    condition: ({ channel, owner, thread }) =>
        channel &&
        owner.props.chatWindow?.isOpen &&
        (thread.is_editable || channel.channel_type === "chat") &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-pencil",
    name: _t("Rename Thread"),
    onSelected: ({ owner }) => (owner.state.editingName = true),
    sequence: 30,
    sequenceGroup: 20,
});
registerThreadAction("close", {
    condition: ({ owner }) => owner.props.chatWindow && !owner.isDiscussSidebarChannelActions,
    icon: "oi fa-fw oi-close",
    name: _t("Close Chat Window (ESC)"),
    onSelected: ({ owner }) => owner.close(),
    sequence: 100,
    sequenceQuick: 10,
});
registerThreadAction("search-messages", {
    actionPanelComponent: SearchMessagesPanel,
    actionPanelOuterClass: "o-mail-SearchMessagesPanel bg-inherit",
    condition: ({ owner, thread }) =>
        ["discuss.channel", "mail.box"].includes(thread?.model) &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    hotkey: "f",
    icon: "oi oi-fw oi-search",
    name: ({ action }) => (action.isActive ? _t("Close Search") : _t("Search Messages")),
    sequence: 20,
    sequenceGroup: 20,
    setup: ({ action }) =>
        useSubEnv({
            searchMenu: {
                open: () => action.actionPanelOpen(),
                close: () => {
                    if (action.isActive) {
                        action.actionPanelClose();
                    }
                },
            },
        }),
});
registerThreadAction("meeting-chat", {
    actionPanelComponent: MeetingChat,
    actionPanelOuterClass: "bg-100 border border-secondary",
    badge: ({ thread }) => thread.isUnread,
    badgeIcon: ({ thread }) => !thread.importantCounter && "fa fa-circle text-700",
    badgeText: ({ thread }) => thread.importantCounter || undefined,
    condition: ({ owner }) => owner.env.inMeetingView,
    icon: "fa fa-fw fa-comments",
    name: _t("Chat"),
    sequence: 30,
    tags: ({ thread }) => {
        const tags = [];
        if (thread.importantCounter) {
            tags.push(ACTION_TAGS.IMPORTANT_BADGE);
        }
        return tags;
    },
});

export class ThreadAction extends Action {
    /** @type {() => Thread} */
    threadFn;

    /**
     * @param {Object} param0
     * @param {Thread|() => Thread} thread
     */
    constructor({ thread }) {
        super(...arguments);
        this.threadFn = typeof thread === "function" ? thread : () => thread;
    }

    get params() {
        const thread = this.threadFn();
        return Object.assign(super.params, { channel: thread?.channel, thread });
    }
}

class UseThreadActions extends UseActions {
    ActionClass = ThreadAction;
}

/**
 * @param {Object} [params0={}]
 * @param {Thread|() => Thread} thread
 */
export function useThreadActions({ thread } = {}) {
    return useAction(threadActionsRegistry, UseThreadActions, ThreadAction, { thread });
}
