import { useSubEnv } from "@web/owl2/utils";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import {
    Action,
    ACTION_TAGS,
    IS_ACTION_DEFINITION_SYM,
    IS_ACTION_GROUP_DESCRIPTION_SYM,
    useAction,
    UseActions,
} from "@mail/core/common/action";
import { RenameThreadPlugin } from "@mail/core/common/rename_thread_plugin";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { MeetingChat } from "@mail/discuss/call/common/meeting_chat";
import { useMaybePlugin } from "@mail/utils/common/hooks";

export const threadActionsRegistry = registry.category("mail.thread/actions");

/**
 * The ids of the thread actions mail registers. A module registering an action of its own names
 * its id where it registers it.
 */
export const THREAD_ACTION_IDS = {
    ADD_TO_FAVORITES: "add-to-favorites",
    ADVANCED_SETTINGS: "advanced-settings",
    ATTACHMENTS: "attachments",
    CALL: "call",
    CALL_SETTINGS: "call-settings",
    CAMERA_CALL: "camera-call",
    CLOSE: "close",
    COPY_INVITE_LINK: "copy-invite-link",
    DELETE_THREAD: "delete-thread",
    DISCONNECT: "disconnect",
    EXPAND_DISCUSS: "expand-discuss",
    FOLD_CHAT_WINDOW: "fold-chat-window",
    HIDE: "hide",
    INVITE_PEOPLE: "invite-people",
    JOIN_CHANNEL: "join-channel",
    LEAVE: "leave",
    MARK_READ: "mark-read",
    MEETING_CHAT: "meeting-chat",
    MEETING_TO_CHAT: "meeting-to-chat",
    MEMBER_LIST: "member-list",
    NOTIFICATION_SETTINGS: "notification-settings",
    PINNED_MESSAGES: "pinned-messages",
    REMOVE_FROM_FAVORITES: "remove-from-favorites",
    RENAME_THREAD: "rename-thread",
    SEARCH_MESSAGES: "search-messages",
    SHOW_THREADS: "show-threads",
    VIEW_RECORDINGS: "view-recordings",
};

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("models").Thread} Thread */
/**
 * @typedef {Object} ThreadActionSpecificParams
 * @property {import("models").DiscussChannel} channel
 * @property {Thread} thread
 */
/** @typedef {import("@mail/core/common/action").ActionParams<ThreadAction, UseThreadActions_Def> & ThreadActionSpecificParams} ThreadActionParams */
/** @typedef {import("@mail/core/common/action").ActionDefinition<ThreadActionParams, ThreadAction>} ThreadActionDefinition */

/**
 * @param {string} id
 * @param {ThreadActionDefinition} definition
 */
export function registerThreadAction(id, definition) {
    threadActionsRegistry.add(id, Object.assign(definition, { [IS_ACTION_DEFINITION_SYM]: true }));
}

/**
 * @param {import("@mail/core/common/action").ActionGroupId} id
 * @param {import("@mail/core/common/action").ActionGroupDescriptionDefinition} definition
 */
export function describeThreadActionGroup(id, definition) {
    threadActionsRegistry.add(
        id,
        Object.assign(definition, { [IS_ACTION_GROUP_DESCRIPTION_SYM]: true })
    );
}

registerThreadAction(THREAD_ACTION_IDS.FOLD_CHAT_WINDOW, {
    btnAttrs: { "data-available-offline": true },
    condition: ({ owner }) => owner.props.chatWindow && !owner.isDiscussSidebarChannelActions,
    icon: "remove",
    name: ({ owner }) => (!owner.props.chatWindow?.isOpen ? _t("Open") : _t("Fold")),
    onSelected: ({ owner }) => owner.toggleFold(),
    displayActive: ({ owner }) => !owner.props.chatWindow?.isOpen,
    sequence: 99,
    sequenceQuick: 20,
});
registerThreadAction(THREAD_ACTION_IDS.RENAME_THREAD, {
    condition: ({ action, channel }) => channel && channel.isAllowedToRename && action.editingName,
    icon: "edit",
    name: _t("Rename Thread"),
    onSelected: ({ action }) => action.editingName.set(true),
    sequence: 30,
    sequenceGroup: 20,
    setup: ({ action }) => (action.editingName = useMaybePlugin(RenameThreadPlugin)?.editingName),
});
registerThreadAction(THREAD_ACTION_IDS.CLOSE, {
    btnAttrs: { "data-available-offline": true },
    condition: ({ owner }) => owner.props.chatWindow && !owner.isDiscussSidebarChannelActions,
    icon: "close_small",
    name: _t("Close Chat Window (ESC)"),
    onSelected: ({ owner }) => owner.close(),
    sequence: 100,
    sequenceQuick: 10,
});
registerThreadAction(THREAD_ACTION_IDS.SEARCH_MESSAGES, {
    actionPanelComponent: SearchMessagesPanel,
    actionPanelComponentProps: ({ thread }) => ({ thread }),
    actionPanelOuterClass: "o-mail-SearchMessagesPanel bg-inherit",
    condition: ({ owner, channel }) =>
        channel &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    hotkey: "f",
    icon: "search",
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
registerThreadAction(THREAD_ACTION_IDS.MEETING_CHAT, {
    actionPanelComponent: MeetingChat,
    actionPanelOuterClass: "bg-100 border",
    badge: ({ thread }) => thread.isUnread,
    badgeIcon: ({ channel }) => !channel.importantCounter && "circle",
    badgeIconClass: ({ channel }) =>
        !channel.importantCounter && "oi-filled o-text-white opacity-75",
    badgeText: ({ channel }) => channel.importantCounter || undefined,
    btnAttrs: { "data-available-offline": true },
    condition: ({ owner }) => owner.env.inMeetingView,
    icon: "forum",
    name: _t("Chat"),
    sequence: 30,
    tags: ({ channel }) => {
        const tags = [];
        if (channel.importantCounter) {
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

/** @typedef {UseActions<ThreadActionParams, ThreadAction>} UseThreadActions_Def */
export class UseThreadActions extends UseActions {
    ActionClass = ThreadAction;
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & {thread?: Thread|() => Thread}} [params0={}]
 * @returns {UseThreadActions_Def}
 */
export function useThreadActions({ thread, rootRef } = {}) {
    return useAction(threadActionsRegistry, UseThreadActions, ThreadAction, { rootRef, thread });
}
