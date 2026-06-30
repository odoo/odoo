import { useSubEnv } from "@web/owl2/utils";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

import { Action, ACTION_TAGS, useAction, UseActions } from "@mail/core/common/action";
import { RenameThreadPlugin } from "@mail/core/common/rename_thread_plugin";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { MeetingChat } from "@mail/discuss/call/common/meeting_chat";
import { maybePlugin } from "@mail/utils/common/misc";

export const threadActionsRegistry = registry.category("mail.thread/actions");

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
    threadActionsRegistry.add(id, definition);
}

registerThreadAction("fold-chat-window", {
    condition: ({ chatWindow, isDiscussSidebarChannelActions }) =>
        chatWindow && !isDiscussSidebarChannelActions,
    icon: "oi oi-fw oi-minus",
    name: ({ chatWindow }) => (!chatWindow?.isOpen ? _t("Open") : _t("Fold")),
    onSelected: ({ toggleFold }) => toggleFold(),
    displayActive: ({ chatWindow }) => !chatWindow?.isOpen,
    sequence: 99,
    sequenceQuick: 20,
});
registerThreadAction("rename-thread", {
    condition: ({ action, channel }) => channel && channel.isAllowedToRename && action.editingName,
    icon: "fa fa-fw fa-pencil",
    name: _t("Rename Thread"),
    onSelected: ({ action }) => action.editingName.set(true),
    sequence: 30,
    sequenceGroup: 20,
    setup: ({ action }) => (action.editingName = maybePlugin(RenameThreadPlugin)?.editingName),
});
registerThreadAction("close", {
    condition: ({ chatWindow, isDiscussSidebarChannelActions }) =>
        chatWindow && !isDiscussSidebarChannelActions,
    icon: "oi fa-fw oi-close",
    name: _t("Close Chat Window (ESC)"),
    onSelected: ({ close }) => close(),
    sequence: 100,
    sequenceQuick: 10,
});
registerThreadAction("search-messages", {
    actionPanelComponent: SearchMessagesPanel,
    actionPanelComponentProps: ({ thread }) => ({ thread }),
    actionPanelOuterClass: "o-mail-SearchMessagesPanel bg-inherit",
    condition: ({ chatWindow, isDiscussSidebarChannelActions, thread }) =>
        ["discuss.channel", "mail.box"].includes(thread?.model) &&
        (!chatWindow || chatWindow.isOpen) &&
        !isDiscussSidebarChannelActions,
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
    badgeIcon: ({ channel }) => !channel.importantCounter && "fa fa-circle o-text-white opacity-75",
    badgeText: ({ channel }) => channel.importantCounter || undefined,
    condition: ({ inMeetingView }) => inMeetingView,
    icon: "fa fa-fw fa-comments",
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
    /** @type {() => import("models").ChatWindow} */
    chatWindowFn;
    /** @type {() => boolean} */
    inDiscussApp;
    /** @type {() => boolean} */
    isDiscussSidebarChannelActions;
    /** @type {() => Thread} */
    threadFn;

    /** @type {() => void} */
    toggleFold;

    /**
     * @param {Object} param0
     * @param {Thread|() => Thread} thread
     */
    constructor({
        chatWindow,
        close,
        homeMenuHasHomeMenu,
        inDiscussApp,
        inMeetingView,
        isDiscussContent,
        isDiscussSidebarChannelActions,
        thread,
        toggleFold,
    }) {
        super(...arguments);
        this.chatWindowFn = typeof chatWindow === "function" ? chatWindow : () => chatWindow;
        this.close = close;
        this.homeMenuHasHomeMenu = homeMenuHasHomeMenu;
        this.inDiscussApp = inDiscussApp;
        this.inMeetingView = inMeetingView;
        this.isDiscussContent = isDiscussContent;
        this.isDiscussSidebarChannelActions = isDiscussSidebarChannelActions;
        this.threadFn = typeof thread === "function" ? thread : () => thread;
        this.toggleFold = toggleFold;
    }

    get params() {
        const thread = this.threadFn();
        return Object.assign(super.params, {
            channel: thread?.channel,
            chatWindow: this.chatWindowFn(),
            close: this.close,
            homeMenuHasHomeMenu: this.homeMenuHasHomeMenu,
            inDiscussApp: this.inDiscussApp?.() ?? false,
            inMeetingView: this.inMeetingView,
            isDiscussContent: this.isDiscussContent,
            isDiscussSidebarChannelActions: this.isDiscussSidebarChannelActions,
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
 * @param {import("@mail/core/common/action").ActionRootRefParam & {thread?: Thread|() => Thread}} [params0={}]
 * @returns {UseThreadActions_Def}
 */
export function useThreadActions({
    chatWindow,
    close,
    homeMenuHasHomeMenu,
    inDiscussApp,
    inMeetingView,
    isDiscussContent,
    isDiscussSidebarChannelActions,
    rootRef,
    thread,
    toggleFold,
} = {}) {
    return useAction(threadActionsRegistry, UseThreadActions, ThreadAction, {
        chatWindow,
        close,
        homeMenuHasHomeMenu,
        inDiscussApp,
        inMeetingView,
        isDiscussContent,
        isDiscussSidebarChannelActions,
        rootRef,
        thread,
        toggleFold,
    });
}
