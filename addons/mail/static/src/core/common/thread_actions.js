import { useSubEnv, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";
import { markEventHandled } from "@web/core/utils/misc";
import { transformDiscussAction } from "./discuss_actions_definition";

export const threadActionsRegistry = registry.category("mail.thread/actions");

threadActionsRegistry
    .add("fold-chat-window", {
        condition(component) {
            return component.props.chatWindow;
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
    })
    .add("rename-thread", {
        condition(component) {
            return (
                component.thread &&
                component.props.chatWindow?.isOpen &&
                (component.thread.is_editable || component.thread.channel_type === "chat")
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
    })
    .add("close", {
        condition(component) {
            return component.props.chatWindow;
        },
        icon: "oi fa-fw oi-close",
        iconLarge: "oi fa-lg fa-fw oi-close",
        name: _t("Close Chat Window (ESC)"),
        open(component) {
            component.close();
        },
        sequence: 100,
        sequenceQuick: 10,
    })
    .add("search-messages", {
        component: SearchMessagesPanel,
        condition(component) {
            return (
                ["discuss.channel", "mail.box"].includes(component.thread?.model) &&
                (!component.props.chatWindow || component.props.chatWindow.isOpen)
            );
        },
        panelOuterClass: "o-mail-SearchMessagesPanel bg-inherit",
        icon: "oi oi-fw oi-search",
        iconLarge: "oi oi-fw fa-lg oi-search",
        name: _t("Search Messages"),
        nameActive: _t("Close Search"),
        sequence: 20,
        sequenceGroup: 20,
        setup(action) {
            useSubEnv({
                searchMenu: {
                    open: () => action.open(),
                    close: () => {
                        if (action.isActive) {
                            action.close();
                        }
                    },
                },
            });
        },
        toggle: true,
    });

function transformAction(component, id, action) {
    return {
        /** Closes this action. */
        close() {
            if (this.toggle) {
                component.threadActions.activeAction = component.threadActions.actionStack.pop();
            }
            action.close?.(component, this);
        },
        /** Optional component that should be displayed in the view when this action is active. */
        component: action.component,
        /** Condition to display the component of this action. */
        get componentCondition() {
            return this.isActive && this.component && this.condition && !this.popover;
        },
        /** Props to pass to the component of this action. */
        get componentProps() {
            return action.componentProps?.(this, component);
        },
        /** Condition to display this action. */
        get condition() {
            return threadActionsInternal.condition(component, id, action);
        },
        /** Condition to disable the button of this action (but still display it). */
        get disabledCondition() {
            return action.disabledCondition?.(component);
        },
        /** Determines whether this action opens a dropdown on selection. Value is shaped { template, menuClass } */
        dropdown: action.dropdown,
        /**
         * Icon for the button this action.
         * - When a string, this is considered an icon as classname (.fa and .oi).
         * - When an object with property `template`, this is an icon rendered in template.
         *   Template params are provided in `params` and passed to template as a `t-set="templateParams"`
         */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        /**
         * Large icon for the button this action.
         * - When a string, this is considered an icon as classname (.fa and .oi).
         * - When an object with property `template`, this is an icon rendered in template.
         *   Template params are provided in `params` and passed to template as a `t-set="templateParams"`
         */
        get iconLarge() {
            return typeof action.iconLarge === "function"
                ? action.iconLarge(component)
                : action.iconLarge ?? action.icon;
        },
        /** States whether this action is currently active. */
        get isActive() {
            return id === component.threadActions.activeAction?.id;
        },
        /** Name of this action, displayed to the user. */
        get name() {
            const res = this.isActive && action.nameActive ? action.nameActive : action.name;
            return typeof res === "function" ? res(component) : res;
        },
        /** ClassName on name of this action */
        get nameClass() {
            return typeof action.nameClass === "function"
                ? action.nameClass(component)
                : action.nameClass;
        },
        /**
         * Action to execute when this action is selected (on or off).
         *
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
        },
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
                if (component.threadActions.activeAction) {
                    if (keepPrevious) {
                        component.threadActions.actionStack.push(
                            component.threadActions.activeAction
                        );
                    } else {
                        component.threadActions.activeAction.close();
                    }
                }
                component.threadActions.activeAction = this;
            }
            action.open?.(component, this);
        },
        get panelOuterClass() {
            return typeof action.panelOuterClass === "function"
                ? action.panelOuterClass(component)
                : action.panelOuterClass;
        },
        /**
         * - In action definition: indicate whether the action is elligible as partition actions. @see useThreadActions::partition
         * - While action is being used: indicate that the action is being used as a partitioned action.
         */
        get partition() {
            if (action._partition) {
                return action._partition;
            }
            return typeof action.partition === "function"
                ? action.partition(component)
                : action.partition ?? true;
        },
        set partition(partition) {
            action._partition = partition;
        },
        /** Determines whether this is a popover linked to this action. */
        popover: null,
        get sequenceGroup() {
            return typeof action.sequenceGroup === "function"
                ? action.sequenceGroup(component)
                : action.sequenceGroup;
        },
        get sequenceQuick() {
            return typeof action.sequenceQuick === "function"
                ? action.sequenceQuick(component)
                : action.sequenceQuick;
        },
        /**
         * - In action definition: indicate whether the action is elligible as sidebar actions. @see useThreadActions::sidebarActions
         * - While action is being used: indicate that the action is being used as a sidebar action.
         */
        sidebar: action.sidebar ?? action.sidebarSequence ?? false,
        sidebarSequence: action.sidebarSequence,
        sidebarSequenceGroup: action.sidebarSequenceGroup,
        /** Text for the button of this action */
        text: action.text,
        /** Determines whether this action is a one time effect or can be toggled (on or off). */
        toggle: action.toggle,
    };
}

export const threadActionsInternal = {
    condition(component, id, action) {
        if (action.condition === undefined) {
            return true;
        }
        return action.condition(component);
    },
};

function makeContextualAction(action, ctx) {
    return Object.assign(Object.create(action), ctx);
}

export function useThreadActions() {
    const component = useComponent();
    const transformedActions = threadActionsRegistry.getEntries().map(([id, action]) => {
        const act = transformAction(component, id, action);
        Object.setPrototypeOf(act, transformDiscussAction(component, id, action));
        return act;
    });
    for (const action of transformedActions) {
        if (action.setup) {
            action.setup(action);
        }
    }
    const state = useState({
        get actions() {
            return transformedActions
                .filter((action) => action.condition && action.sequence !== undefined)
                .map((action) => makeContextualAction(action, { partition: false, sidebar: false }))
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
        get sidebarActions() {
            const actions = transformedActions
                .filter((action) => action.condition && action.sidebarSequence !== undefined)
                .sort((action1, action2) => action1.sidebarSequence - action2.sidebarSequence)
                .map((action) => makeContextualAction(action, { partition: false, sidebar: true }));
            const groups = {};
            for (const a of actions) {
                if (!(a.sidebarSequenceGroup in groups)) {
                    groups[a.sidebarSequenceGroup] = [];
                }
                groups[a.sidebarSequenceGroup].push(a);
            }
            const sortedGroups = Object.entries(groups).sort(([g1, g2]) => g1 - g2);
            for (const [, actions] of sortedGroups) {
                actions.sort((a1, a2) => a1.sidebarSequence - a2.sidebarSequence);
            }
            return sortedGroups.map(([g1, actions]) => actions);
        },
        get partition() {
            const actions = transformedActions
                .filter((action) => action.condition && action.partition)
                .map((action) => makeContextualAction(action, { partition: true, sidebar: false }));
            const quick = actions
                .filter((a) => a.sequenceQuick)
                .sort((a1, a2) => a1.sequenceQuick - a2.sequenceQuick);
            const grouped = actions.filter((a) => a.sequenceGroup);
            const groups = {};
            for (const a of grouped) {
                if (!(a.sequenceGroup in groups)) {
                    groups[a.sequenceGroup] = [];
                }
                groups[a.sequenceGroup].push(a);
            }
            const sortedGroups = Object.entries(groups).sort(
                ([groupId1], [groupId2]) => groupId1 - groupId2
            );
            for (const [, actions] of sortedGroups) {
                actions.sort((a1, a2) => a1.sequence - a2.sequence);
            }
            const group = sortedGroups.map(([groupId, actions]) => actions);
            const other = actions
                .filter((a) => !a.sequenceQuick && !a.sequenceGroup)
                .sort((a1, a2) => a1.sequence - a2.sequence);
            return { quick, group, other };
        },
        actionStack: [],
        activeAction: null,
    });
    return state;
}
