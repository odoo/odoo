import { Action as ActionModel } from "@mail/core/common/action";
import {
    ActionButton,
    actionButtonProps,
    actionButtonPropsSchema,
} from "@mail/core/common/action_button";
import { ActionDropdown } from "@mail/core/common/action_dropdown";
import { propSignal } from "@mail/utils/common/hooks";
import { Component, computed, onWillUnmount, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useService } from "@web/core/utils/hooks";

const actionListProps = actionButtonProps;
const actionListPropsSchema = actionButtonPropsSchema;

/**
 * Wraps an action's chrome (rendered generically by {@link ActionButton}) with
 * its optional own dropdown, e.g. a "more actions" overflow menu.
 */
class Action extends Component {
    static components = { ActionButton, ActionDropdown };
    static template = "mail.Action";

    get ActionList() {
        return ActionList;
    }

    get Dropdown() {
        return Dropdown;
    }

    setup() {
        super.setup();
        this.props = useProps({
            action: t.instanceOf(ActionModel),
            style: t.string().optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        if (this.props.action.definition?.isMoreAction) {
            onWillUnmount(() => {
                this.props.action.dropdownState.close();
            });
        }
    }

    get action() {
        return this.props.action;
    }
}

export class ActionList extends Component {
    static components = { Action };
    static template = "mail.ActionList";

    getActionProps(action, group, { index } = {}) {
        return {
            action,
            group,
            ...Object.fromEntries(
                actionListProps.map((propName) => {
                    const actualPropName = propName.endsWith("?")
                        ? propName.substring(0, propName.length - 1)
                        : propName;
                    return [actualPropName, this.props[actualPropName]];
                })
            ),
            style: `z-index: ${group.length - index + (action.hotkey ? 1 : 0)}`,
        };
    }

    setup() {
        super.setup();
        this.actions = propSignal(
            "actions",
            t.array(t.or([t.instanceOf(ActionModel), t.array(t.instanceOf(ActionModel))]))
        );
        this.props = useProps({
            groupClass: t.string().optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.actionListProps = actionListProps;
    }

    groups = computed(() => {
        const actions = this.actions();
        let groups;
        if (actions.find((i) => Array.isArray(i))) {
            groups = actions;
        } else {
            groups = [actions];
        }
        return groups.filter((group) => group.length); // don't show empty groups
    });
}
