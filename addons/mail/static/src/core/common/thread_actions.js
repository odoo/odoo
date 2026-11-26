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
import { useAncestors } from "@mail/core/common/ancestor_plugin";
import { RenameThreadPlugin } from "@mail/core/common/rename_thread_plugin";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { MeetingChat } from "@mail/discuss/call/common/meeting_chat";
import { useMaybePlugin } from "@mail/utils/common/hooks";

export const threadActionsRegistry = registry.category("mail.thread/actions");

/** @typedef {import("models").ChatWindow} ChatWindow */
/** @typedef {import("models").Thread} Thread */
/**
 * @typedef {Object} ThreadActionSpecificParams
 * @property {import("models").DiscussChannel} channel
 * @property {Thread} thread
 * @property {ChatWindow} [chatWindow] the chat window showing the action
 * @property {() => void} [toggleFold] folds or unfolds that chat window
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

registerThreadAction("fold-chat-window", {
    availableOffline: true,
    condition: ({ ancestors }) => ancestors.inChatWindow && !ancestors.inMessagingMenu,
    icon: "remove",
    name: _t("Fold"),
    onSelected: ({ toggleFold }) => toggleFold(),
    sequence: 99,
    sequenceQuick: 20,
});
registerThreadAction("rename-thread", {
    condition: ({ action, channel }) => channel && channel.isAllowedToRename && action.editingName,
    icon: "edit",
    name: _t("Rename Thread"),
    onSelected: ({ action }) => action.editingName.set(true),
    sequence: 30,
    sequenceGroup: 20,
    setup: ({ action }) => (action.editingName = useMaybePlugin(RenameThreadPlugin)?.editingName),
});
registerThreadAction("close", {
    availableOffline: true,
    condition: ({ ancestors }) => ancestors.inChatWindow && !ancestors.inMessagingMenu,
    icon: "close_small",
    name: _t("Close Chat Window (ESC)"),
    onSelected: ({ chatWindow }) => chatWindow.requestClose(),
    sequence: 100,
    sequenceQuick: 10,
});
registerThreadAction("search-messages", {
    condition: ({ ancestors, channel }) => channel && !ancestors.inMessagingMenu,
    hotkey: "f",
    icon: "search",
    name: ({ action }) => (action.isActive ? _t("Close Search") : _t("Search Messages")),
    panel: {
        component: SearchMessagesPanel,
        props: ({ thread }) => ({ thread }),
    },
    sequence: ({ ancestors }) => (ancestors.inDiscussContent ? 1 : 20),
    sequenceGroup: ({ ancestors }) => (ancestors.inDiscussContent ? 10 : 20),
});
registerThreadAction("meeting-chat", {
    availableOffline: true,
    badge: ({ thread }) => thread.isUnread,
    badgeIcon: ({ channel }) => !channel.importantCounter && "circle",
    badgeIconClass: ({ channel }) =>
        !channel.importantCounter && "oi-filled o-text-white opacity-75",
    badgeText: ({ channel }) => channel.importantCounter || undefined,
    condition: ({ ancestors }) => ancestors.inMeetingView,
    icon: "forum",
    name: _t("Chat"),
    panel: { component: MeetingChat },
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
    /** @type {() => ChatWindow|undefined} */
    chatWindowFn;
    /** @type {() => Thread} */
    threadFn;
    /** @type {(() => void)|undefined} */
    toggleFold;

    /**
     * @param {Object} param0
     * @param {ChatWindow|() => ChatWindow} [param0.chatWindow]
     * @param {Thread|() => Thread} param0.thread
     * @param {() => void} [param0.toggleFold]
     */
    constructor({ chatWindow, thread, toggleFold }) {
        super(...arguments);
        this.chatWindowFn = typeof chatWindow === "function" ? chatWindow : () => chatWindow;
        this.threadFn = typeof thread === "function" ? thread : () => thread;
        this.toggleFold = toggleFold;
    }

    get params() {
        const thread = this.threadFn();
        return Object.assign(super.params, {
            channel: thread?.channel,
            chatWindow: this.chatWindowFn(),
            thread,
            toggleFold: this.toggleFold,
        });
    }
}

/** @typedef {UseActions<ThreadActionParams, ThreadAction>} UseThreadActions_Def */
export class UseThreadActions extends UseActions {
    ActionClass = ThreadAction;
}

/**
 * @param {import("@mail/core/common/action").ActionRootRefParam & {chatWindow?: ChatWindow|() => ChatWindow, thread?: Thread|() => Thread, toggleFold?: () => void}} [params0={}]
 *   `chatWindow`: when set, the chat window showing the actions. `toggleFold`: when set, folds or
 *   unfolds that chat window.
 * @returns {UseThreadActions_Def}
 */
export function useThreadActions({ chatWindow, rootRef, thread, toggleFold } = {}) {
    const actions = useAction(threadActionsRegistry, UseThreadActions, ThreadAction, {
        chatWindow,
        rootRef,
        thread,
        toggleFold,
    });
    useAncestors({ threadActions: actions });
    return actions;
}
