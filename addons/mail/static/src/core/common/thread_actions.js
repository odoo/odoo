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
 * @property {import("models").ChatWindow} [chatWindow]
 * @property {() => void} [close]
 * @property {string} [discussDropdownMenuClass]
 * @property {boolean} [hasHomeMenu]
 * @property {boolean} [inChatWindow]
 * @property {boolean} [inDiscussApp]
 * @property {object} [inMeetingView]
 * @property {boolean} [isDiscussContent]
 * @property {boolean} [isDiscussSidebarChannelActions]
 * @property {Window} [pipWindow]
 * @property {Thread} thread
 * @property {() => void} [toggleFold]
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
    btnAttrs: { "data-available-offline": true },
    condition: ({ chatWindow }) => Boolean(chatWindow),
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
    btnAttrs: { "data-available-offline": true },
    condition: ({ chatWindow }) => Boolean(chatWindow),
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
    condition: ({ channel, chatWindow, isDiscussSidebarChannelActions }) =>
        channel && (!chatWindow || chatWindow.isOpen) && !isDiscussSidebarChannelActions,
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
    btnAttrs: { "data-available-offline": true },
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
    /** @type {() => void} */
    close;
    /** @type {() => string} */
    discussDropdownMenuClass;
    /** @type {() => boolean} */
    hasHomeMenuFn;
    /** @type {boolean} */
    inChatWindow;
    /** @type {boolean} */
    inDiscussApp;
    /** @type {object} */
    inMeetingView;
    /** @type {boolean} */
    isDiscussContent;
    /** @type {boolean} */
    isDiscussSidebarChannelActions;
    /** @type {() => Window} */
    pipWindow;
    /** @type {() => Thread} */
    threadFn;
    /** @type {() => void} */
    toggleFold;

    /**
     * @param {Object} param0
     * @param {() => import("models").ChatWindow} [param0.chatWindow]
     * @param {() => void} [param0.close]
     * @param {() => string} [param0.discussDropdownMenuClass]
     * @param {() => boolean} [param0.hasHomeMenu]
     * @param {boolean} [param0.inChatWindow]
     * @param {boolean} [param0.inDiscussApp]
     * @param {object} [param0.inMeetingView]
     * @param {boolean} [param0.isDiscussContent]
     * @param {boolean} [param0.isDiscussSidebarChannelActions]
     * @param {() => Window} [param0.pipWindow]
     * @param {Thread|() => Thread} param0.thread
     * @param {() => void} [param0.toggleFold]
     */
    constructor({
        chatWindow,
        close,
        discussDropdownMenuClass,
        hasHomeMenu,
        inChatWindow,
        inDiscussApp,
        inMeetingView,
        isDiscussContent,
        isDiscussSidebarChannelActions,
        pipWindow,
        thread,
        toggleFold,
    }) {
        super(...arguments);
        this.chatWindowFn = chatWindow;
        this.close = close;
        this.discussDropdownMenuClass = discussDropdownMenuClass;
        this.hasHomeMenuFn = hasHomeMenu;
        this.inChatWindow = inChatWindow;
        this.inDiscussApp = inDiscussApp;
        this.inMeetingView = inMeetingView;
        this.isDiscussContent = isDiscussContent;
        this.isDiscussSidebarChannelActions = isDiscussSidebarChannelActions;
        this.pipWindow = pipWindow;
        this.threadFn = typeof thread === "function" ? thread : () => thread;
        this.toggleFold = toggleFold;
    }

    get params() {
        const thread = this.threadFn();
        return Object.assign(super.params, {
            channel: thread?.channel,
            chatWindow: this.chatWindowFn?.(),
            close: this.close,
            discussDropdownMenuClass: this.discussDropdownMenuClass?.(),
            hasHomeMenu: this.hasHomeMenuFn?.(),
            inChatWindow: this.inChatWindow,
            inDiscussApp: this.inDiscussApp,
            inMeetingView: this.inMeetingView,
            isDiscussContent: this.isDiscussContent,
            isDiscussSidebarChannelActions: this.isDiscussSidebarChannelActions,
            pipWindow: this.pipWindow?.(),
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
 * @param {import("@mail/core/common/action").ActionRootRefParam & {
 *   chatWindow?: () => import("models").ChatWindow,
 *   close?: () => void,
 *   discussDropdownMenuClass?: () => string,
 *   hasHomeMenu?: () => boolean,
 *   inChatWindow?: boolean,
 *   inDiscussApp?: boolean,
 *   inMeetingView?: object,
 *   isDiscussContent?: boolean,
 *   isDiscussSidebarChannelActions?: boolean,
 *   pipWindow?: () => Window,
 *   thread?: Thread|() => Thread,
 *   toggleFold?: () => void,
 * }} [params0={}]
 * @returns {UseThreadActions_Def}
 */
export function useThreadActions({
    chatWindow,
    close,
    discussDropdownMenuClass,
    hasHomeMenu,
    inChatWindow,
    inDiscussApp,
    inMeetingView,
    isDiscussContent,
    isDiscussSidebarChannelActions,
    pipWindow,
    rootRef,
    thread,
    toggleFold,
} = {}) {
    return useAction(threadActionsRegistry, UseThreadActions, ThreadAction, {
        chatWindow,
        close,
        discussDropdownMenuClass,
        hasHomeMenu,
        inChatWindow,
        inDiscussApp,
        inMeetingView,
        isDiscussContent,
        isDiscussSidebarChannelActions,
        pipWindow,
        rootRef,
        thread,
        toggleFold,
    });
}
