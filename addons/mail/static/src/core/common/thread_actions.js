import { useSubEnv, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { markEventHandled } from "@web/core/utils/misc";
import { Action, ACTION_TAGS, UseActions } from "@mail/core/common/action";
import { MeetingChat } from "@mail/discuss/call/common/meeting_chat";
import { useService } from "@web/core/utils/hooks";

export const threadActionsRegistry = registry.category("mail.thread/actions");

/** @typedef {import("@odoo/owl").Component} Component */
/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */
/** @typedef {import("models").Thread} Thread */
/**
 * @typedef {Object} ThreadActionSpecificDefinition
 * @property {Component} [actionPanelComponent]
 * @property {(Component) => Object} [actionPanelComponentProps]
 * @property {(Component) => void} [close]
 * @property {boolean|(comp: Component) => boolean} [condition=true]
 * @property {string|(comp: Component) => string} [nameClass]
 * @property {(comp: Component) => void} [open]
 * @property {(comp: Component) => string} [panelOuterClass]
 * @property {boolean} [toggle]
 */

/**
 * @typedef {ActionDefinition & ThreadActionSpecificDefinition} ThreadActionDefinition
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
    open: ({ owner }) => owner.toggleFold(),
    displayActive: ({ owner }) => !owner.props.chatWindow?.isOpen,
    sequence: 99,
    sequenceQuick: 20,
});
registerThreadAction("rename-thread", {
    condition: ({ owner, thread }) =>
        thread &&
        owner.props.chatWindow?.isOpen &&
        (thread.is_editable || thread.channel_type === "chat") &&
        !owner.isDiscussSidebarChannelActions,
    icon: "fa fa-fw fa-pencil",
    name: _t("Rename Thread"),
    open: ({ owner }) => (owner.state.editingName = true),
    sequence: 30,
    sequenceGroup: 20,
});
registerThreadAction("close", {
    condition: ({ owner }) => owner.props.chatWindow && !owner.isDiscussSidebarChannelActions,
    icon: "oi fa-fw oi-close",
    name: _t("Close Chat Window (ESC)"),
    open: ({ owner }) => owner.close(),
    sequence: 100,
    sequenceQuick: 10,
});
registerThreadAction("search-messages", {
    actionPanelComponent: SearchMessagesPanel,
    condition: ({ owner, thread }) =>
        ["discuss.channel", "mail.box"].includes(thread?.model) &&
        (!owner.props.chatWindow || owner.props.chatWindow.isOpen) &&
        !owner.isDiscussSidebarChannelActions,
    hotkey: "f",
    panelOuterClass: "o-mail-SearchMessagesPanel bg-inherit",
    icon: "oi oi-fw oi-search",
    name: ({ action }) => (action.isActive ? _t("Close Search") : _t("Search Messages")),
    sequence: 20,
    sequenceGroup: 20,
    setup: ({ action }) =>
        useSubEnv({
            searchMenu: {
                open: () => action.open(),
                close: () => {
                    if (action.isActive) {
                        action.close();
                    }
                },
            },
        }),
    toggle: true,
});
registerThreadAction("meeting-chat", {
    actionPanelComponent: MeetingChat,
    badge: ({ thread }) => thread.isUnread,
    badgeIcon: ({ thread }) => !thread.importantCounter && "fa fa-circle text-700",
    badgeText: ({ thread }) => thread.importantCounter || undefined,
    condition: ({ owner }) => owner.env.inMeetingView,
    icon: "fa fa-fw fa-comments",
    name: _t("Chat"),
    panelOuterClass: "bg-100 border border-secondary",
    sequence: 30,
    toggle: true,
    tags: ({ thread }) => {
        const tags = [];
        if (thread.importantCounter) {
            tags.push(ACTION_TAGS.IMPORTANT_BADGE);
        }
        return tags;
    },
});

export class ThreadAction extends Action {
    /** Determines whether this is a popover linked to this action. */
    popover = null;
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
        return Object.assign(super.params, { thread: this.threadFn() });
    }

    /** Optional component that is used as action panel of this component, i.e. when action is active. */
    get actionPanelComponent() {
        return this.definition.actionPanelComponent;
    }

    /** Condition to display the action panel component of this action. */
    get actionPanelComponentCondition() {
        return this.isActive && this.actionPanelComponent && this.condition && !this.popover;
    }

    /** Props to pass to the action panel component of this action. */
    get actionPanelComponentProps() {
        return this.definition.actionPanelComponentProps?.call(this, this.params);
    }

    /** Closes this action. */
    close({ nextActiveAction } = {}) {
        if (this.toggle) {
            this.owner.threadActions.activeAction = this.owner.threadActions.actionStack.pop();
        }
        this.definition.close?.call(this, Object.assign(this.params, { nextActiveAction }));
    }

    /** States whether this action is currently active. */
    get isActive() {
        return this.id === this.owner.threadActions.activeAction?.id;
    }

    /** ClassName on name of this action */
    get nameClass() {
        return typeof this.definition.nameClass === "function"
            ? this.definition.nameClass.call(this, this.params)
            : this.definition.nameClass;
    }

    /**
     * @override
     * @param {MouseEvent} [ev]
     * @param {object} [param0]
     * @param {boolean} [param0.keepPrevious] Whether the previous action
     * should be kept so that closing the current action goes back
     * to the previous one.
     * */
    onSelected(ev, { keepPrevious } = {}) {
        if (ev) {
            markEventHandled(ev, "ThreadAction.onSelected");
        }
        if (this.toggle && this.isActive) {
            this.close();
        } else {
            this.open({ keepPrevious });
        }
    }

    /**
     * Opens this action.
     *
     * @param {object} [param0]
     * @param {boolean} [param0.keepPrevious] Whether the previous action
     * should be kept so that closing the current action goes back
     * to the previous one.
     * */
    open({ keepPrevious } = {}) {
        if (this.toggle) {
            if (this.owner.threadActions.activeAction) {
                if (keepPrevious) {
                    this.owner.threadActions.actionStack.push(
                        this.owner.threadActions.activeAction
                    );
                } else {
                    this.owner.threadActions.activeAction.close({ nextActiveAction: this });
                }
            }
            this.owner.threadActions.activeAction = this;
        }
        this.definition.open?.call(this, this.params);
    }

    get panelOuterClass() {
        return typeof this.definition.panelOuterClass === "function"
            ? this.definition.panelOuterClass.call(this, this.params)
            : this.definition.panelOuterClass;
    }

    /** Determines whether this action is a one time effect or can be toggled (on or off). */
    get toggle() {
        return this.definition.toggle;
    }
}

class UseThreadActions extends UseActions {
    ActionClass = ThreadAction;
    actionStack = [];
    activeAction = null;
}

/**
 * @param {Object} [params0={}]
 * @param {Thread|() => Thread} thread
 */
export function useThreadActions({ thread } = {}) {
    const component = useComponent();
    const transformedActions = threadActionsRegistry
        .getEntries()
        .map(([id, definition]) => new ThreadAction({ owner: component, id, definition, thread }));
    for (const action of transformedActions) {
        action.setup();
    }
    return useState(new UseThreadActions(component, transformedActions, useService("mail.store")));
}
