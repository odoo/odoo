import { propSignal } from "@mail/utils/common/hooks";
import { Component, computed, onWillUnmount, t, useProps } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { Action as ActionModel } from "@mail/core/common/action";
import { ActionButton } from "@mail/core/common/action_button";
import { ActionDropdown } from "@mail/core/common/action_dropdown";
import { useService } from "@web/core/utils/hooks";

const actionListProps = [
    "inline?",
    "dropdown?",
    "fw?",
    "hasBtnBg?",
    "odooControlPanelSwitchStyle?",
];

const actionListPropsSchema = {
    dropdown: t.boolean().optional(),
    fw: t.boolean().optional(true),
    hasBtnBg: t.boolean().optional(),
    inline: t.boolean().optional(),
    odooControlPanelSwitchStyle: t.boolean().optional(),
};

class Action extends Component {
    static components = { Action, ActionButton, ActionDropdown };
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
            isFirstInGroup: t.boolean().optional(),
            isLastInGroup: t.boolean().optional(),
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

    onSelected(action, ev) {
        action.onSelected?.(ev);
        this.env.inCallDropdown?.close();
    }
}

export class ActionList extends Component {
    static components = { Action };
    static template = "mail.ActionList";

    getActionProps(action, group, { index, isFirstInGroup, isLastInGroup } = {}) {
        return {
            action,
            group,
            isFirstInGroup,
            isLastInGroup,
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

    get hasBtnBg() {
        return this.props.odooControlPanelSwitchStyle || this.props.hasBtnBg;
    }
}
