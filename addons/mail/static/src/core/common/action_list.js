import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, onWillDestroy, onWillUnmount, props, t } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Action as ActionModel } from "@mail/core/common/action";
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

export class Action extends Component {
    static components = { Action, DropdownItem };
    static template = "mail.Action";

    get ActionList() {
        return ActionList;
    }

    get Dropdown() {
        return Dropdown;
    }

    setup() {
        super.setup();
        this.props = props({
            action: t.instanceOf(ActionModel),
            isFirstInGroup: t.boolean().optional(),
            isLastInGroup: t.boolean().optional(),
            style: t.string().optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.attClassObjectToString = attClassObjectToString;
        this.props.action.setRenderingContext(this);
        if (this.props.action.definition?.isMoreAction) {
            onWillUnmount(() => {
                this.props.action.dropdownState.close();
            });
        }
        onWillDestroy(() => {
            this.props.action.unsetRenderingContext();
        });
    }

    get action() {
        return this.props.action;
    }

    get hasBtnBg() {
        return (
            this.props.odooControlPanelSwitchStyle ||
            this.props.hasBtnBg ||
            this.props.action.hasBtnBg
        );
    }

    get isInlineCircleButtonValue() {
        if (!this.props.inline || !this.action.icon) {
            return false;
        }
        if (this.env.inComposer || this.env.inMessage) {
            return true;
        }
        return (
            this.action.tags.includes("JOIN_LEAVE_CALL") &&
            this.action.icon &&
            !this.action.inlineName
        );
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
        this.props = props({
            actions: t.array(t.or([t.instanceOf(ActionModel), t.array(t.instanceOf(ActionModel))])),
            groupClass: t.string().optional(),
            ...actionListPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.actionListProps = actionListProps;
    }

    get groups() {
        let groups;
        if (this.props.actions.find((i) => Array.isArray(i))) {
            groups = this.props.actions;
        } else {
            groups = [this.props.actions];
        }
        return groups.filter((group) => group.length); // don't show empty groups
    }

    get hasBtnBg() {
        return this.props.odooControlPanelSwitchStyle || this.props.hasBtnBg;
    }
}
