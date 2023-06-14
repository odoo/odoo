/* @odoo-module */

import { useComponent, useState } from "@odoo/owl";

import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";

export const threadActionsRegistry = registry.category("mail.thread/actions");

threadActionsRegistry.add("close", {
    condition(component) {
        return component.props.chatWindow;
    },
    icon: "fa fa-fw fa-close",
    name: _t("Close Chat Window"),
    open(component) {
        component.close();
    },
    sequence: 100,
});

function transformAction(component, id, action) {
    return {
        /** Closes this action. */
        close() {
            if (this.toggle) {
                component.threadActions.activeAction = null;
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
            return action.componentProps?.(this);
        },
        /** Condition to display this action. */
        get condition() {
            return action.condition(component);
        },
        /** Condition to disable the button of this action (but still display it). */
        get disabledCondition() {
            return action.disabledCondition?.(component);
        },
        /** Icon for the button this action. */
        icon: action.icon,
        /** Large icon for the button this action. */
        iconLarge: action.iconLarge ?? action.icon,
        /** Unique id of this action. */
        id,
        /** States whether this action is currently active. */
        get isActive() {
            return id === component.threadActions.activeAction?.id;
        },
        /** Name of this action, displayed to the user. */
        get name() {
            return this.isActive && action.nameActive ? action.nameActive : action.name;
        },
        /** Action to execute when this action is selected (on or off). */
        onSelect() {
            if (this.toggle && this.isActive) {
                this.close();
            } else {
                this.open();
            }
        },
        /** Opens this action. */
        open() {
            if (this.toggle) {
                component.threadActions.activeAction = this;
            }
            action.open?.(component, this);
        },
        /** Determines whether this is a popover linked to this action. */
        popover: null,
        /** Determines the order of this action (smaller first). */
        get sequence() {
            return typeof action.sequence === "function"
                ? action.sequence(component)
                : action.sequence;
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
        activeAction: null,
    });
    return state;
}
