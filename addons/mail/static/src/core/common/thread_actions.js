import { useSubEnv, useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { SearchMessagesPanel } from "@mail/core/common/search_messages_panel";

export const threadActionsRegistry = registry.category("mail.thread/actions");

threadActionsRegistry
    .add("fold-chat-window", {
        condition(component) {
            return (
                component.props.chatWindow &&
                component.props.chatWindow.thread &&
                (component.env.services["im_livechat.livechat"] ||
                    !component.env.services.ui.isSmall)
            );
        },
        icon: "fa fa-fw fa-minus",
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
            if (action.condition === undefined) {
                return true;
            }
            return action.condition(component);
        },
        /** Condition to disable the button of this action (but still display it). */
        get disabledCondition() {
            return action.disabledCondition?.(component);
        },
        /** Icon for the button this action. */
        get icon() {
            return typeof action.icon === "function" ? action.icon(component) : action.icon;
        },
        /** Large icon for the button this action. */
        get iconLarge() {
            return typeof action.iconLarge === "function"
                ? action.iconLarge(component)
                : action.iconLarge ?? action.icon;
        },
        /** Unique id of this action. */
        id,
        /** States whether this action is currently active. */
        get isActive() {
            return id === component.threadActions.activeAction?.id;
        },
        /** Name of this action, displayed to the user. */
        get name() {
            const res = this.isActive && action.nameActive ? action.nameActive : action.name;
            return typeof res === "function" ? res(component) : res;
        },
        /**
         * Action to execute when this action is selected (on or off).
         *
         * @param {object} [param0]
         * @param {boolean} [param0.keepPrevious] Whether the previous action
         * should be kept so that closing the current action goes back
         * to the previous one.
         * */
        onSelect({ keepPrevious } = {}) {
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
        /** Determines whether this is a popover linked to this action. */
        popover: null,
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
        },
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
        /** Component setup to execute when this action is registered. */
        setup: action.setup,
        /** Text for the button of this action */
        text: action.text,
        /** Determines whether this action is a one time effect or can be toggled (on or off). */
        toggle: action.toggle,
    };
}

export function useThreadActions() {
    const component = useComponent();
    const transformedActions = threadActionsRegistry
        .getEntries()
        .map(([id, action]) => transformAction(component, id, action));
    for (const action of transformedActions) {
        if (action.setup) {
            action.setup(action);
        }
    }
    const state = useState({
        get actions() {
            return transformedActions
                .filter((action) => action.condition)
                .sort((a1, a2) => a1.sequence - a2.sequence);
        },
        get partition() {
            const actions = transformedActions.filter((action) => action.condition);
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
                .filter((a) => !a.sequenceQuick & !a.sequenceGroup)
                .sort((a1, a2) => a1.sequence - a2.sequence);
            return { quick, group, other };
        },
        actionStack: [],
        activeAction: null,
    });
    return state;
}
