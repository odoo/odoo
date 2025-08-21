import { useSubEnv, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { markEventHandled } from "@web/core/utils/misc";
import { Action, UseActions } from "./action";

export const threadActionsRegistry = registry.category("mail.thread/actions");

/** @typedef {import("@odoo/owl").Component} Component */

/** @typedef {import("@mail/core/common/action").ActionDefinition} ActionDefinition */

/**
 * @typedef {Object} ThreadActionSpecificDefinition
 * @property {Component} [actionPanelComponent]
 * @property {(Component) => Object} [actionPanelComponentProps]
 * @property {(Component) => void} [close]
 * @property {boolean|(comp: Component) => boolean} [condition=true]
 * @property {string} [nameActive]
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
    condition(component) {
        return component.props.chatWindow && !component.isDiscussSidebarChannelActions;
    },
    icon: "oi oi-fw oi-minus",
    iconLarge: "oi oi-fw fa-lg oi-minus",
    name(component) {
        return !component.props.chatWindow?.isOpen ? _t("Open") : _t("Fold");
    },
    open(component) {
        component.toggleFold();
    },
    displayActive(component) {
        return !component.props.chatWindow?.isOpen;
    },
    sequence: 99,
    sequenceQuick: 20,
});
registerThreadAction("rename-thread", {
    condition(component) {
        return (
            component.thread &&
            component.props.chatWindow?.isOpen &&
            (component.thread.is_editable || component.thread.channel_type === "chat") &&
            !component.isDiscussSidebarChannelActions
        );
    },
    icon: "fa fa-fw fa-pencil",
    iconLarge: "fa fa-lg fa-fw fa-pencil",
    name: _t("Rename Thread"),
    open(component) {
        component.state.editingName = true;
    },
    sequence: 30,
    sequenceGroup: 20,
});
registerThreadAction("close", {
    condition(component) {
        return component.props.chatWindow && !component.isDiscussSidebarChannelActions;
    },
    icon: "oi fa-fw oi-close",
    iconLarge: "oi fa-lg fa-fw oi-close",
    name: _t("Close Chat Window (ESC)"),
    open(component) {
        component.close();
    },
    sequence: 100,
    sequenceQuick: 10,
});
registerThreadAction("search-messages", {
    actionPanelComponent: SearchMessagesPanel,
    condition(component) {
        return (
            ["discuss.channel", "mail.box"].includes(component.thread?.model) &&
            (!component.props.chatWindow || component.props.chatWindow.isOpen) &&
            !component.isDiscussSidebarChannelActions
        );
    },
    panelOuterClass: "o-mail-SearchMessagesPanel bg-inherit",
    icon: "oi oi-fw oi-search",
    iconLarge: "oi oi-fw fa-lg oi-search",
    name: _t("Search Messages"),
    nameActive: _t("Close Search"),
    sequence: 20,
    sequenceGroup: 20,
    setup() {
        useSubEnv({
            searchMenu: {
                open: () => this.open(),
                close: () => {
                    if (this.isActive) {
                        this.close();
                    }
                },
            },
        });
    },
    toggle: true,
});

class ThreadAction extends Action {
    /** Determines whether this is a popover linked to this action. */
    popover = null;

    /** Optional component that is used as action panel of this component, i.e. when action is active. */
    get actionPanelComponent() {
        return this.explicitDefinition.actionPanelComponent;
    }

    /** Condition to display the action panel component of this action. */
    get actionPanelComponentCondition() {
        return this.isActive && this.actionPanelComponent && this.condition && !this.popover;
    }

    /** Props to pass to the action panel component of this action. */
    get actionPanelComponentProps() {
        return this.explicitDefinition.actionPanelComponentProps?.(this._component, this);
    }

    /** Closes this action. */
    close() {
        if (this.toggle) {
            this._component.threadActions.activeAction =
                this._component.threadActions.actionStack.pop();
        }
        this.explicitDefinition.close?.(this._component, this);
    }

    /** Condition to display this action. */
    get condition() {
        return threadActionsInternal.condition(this._component, this.id, this.explicitDefinition);
    }

    /** States whether this action is currently active. */
    get isActive() {
        return this.id === this._component.threadActions.activeAction?.id;
    }

    /** @override **/
    get name() {
        const res =
            this.isActive && this.explicitDefinition.nameActive
                ? this.explicitDefinition.nameActive
                : this.explicitDefinition.name;
        return typeof res === "function" ? res(this._component) : res;
    }

    /** ClassName on name of this action */
    get nameClass() {
        return typeof this.explicitDefinition.nameClass === "function"
            ? this.explicitDefinition.nameClass(this._component)
            : this.explicitDefinition.nameClass;
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
            markEventHandled(ev, "DiscussAction.onSelected");
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
            if (this._component.threadActions.activeAction) {
                if (keepPrevious) {
                    this._component.threadActions.actionStack.push(
                        this._component.threadActions.activeAction
                    );
                } else {
                    this._component.threadActions.activeAction.close();
                }
            }
            this._component.threadActions.activeAction = this;
        }
        this.explicitDefinition.open?.(this._component, this);
    }

    get panelOuterClass() {
        return typeof this.explicitDefinition.panelOuterClass === "function"
            ? this.explicitDefinition.panelOuterClass(this._component)
            : this.explicitDefinition.panelOuterClass;
    }

    get sequenceGroup() {
        return typeof this.explicitDefinition.sequenceGroup === "function"
            ? this.explicitDefinition.sequenceGroup(this._component)
            : this.explicitDefinition.sequenceGroup;
    }

    get sequenceQuick() {
        return typeof this.explicitDefinition.sequenceQuick === "function"
            ? this.explicitDefinition.sequenceQuick(this._component)
            : this.explicitDefinition.sequenceQuick;
    }

    /** Determines whether this action is a one time effect or can be toggled (on or off). */
    get toggle() {
        return this.explicitDefinition.toggle;
    }
}

export const threadActionsInternal = {
    condition(component, id, action) {
        if (!action?.condition) {
            return true;
        }
        return typeof action.condition === "function"
            ? action.condition(component)
            : action.condition;
    },
};

class UseThreadActions extends UseActions {
    ActionClass = ThreadAction;
    actionStack = [];
    activeAction = null;
}

export function useThreadActions() {
    const component = useComponent();
    const transformedActions = threadActionsRegistry
        .getEntries()
        .map(([id, action]) => new ThreadAction(component, id, action));
    for (const action of transformedActions) {
        action.setup();
    }
    return useState(new UseThreadActions(component, transformedActions));
}
