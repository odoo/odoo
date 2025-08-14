import { CallDropdown } from "@mail/discuss/call/common/call_dropdown";
import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, onWillUnmount, useEffect } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";

import { useService } from "@web/core/utils/hooks";

const actionListProps = [
    "inline?",
    "dropdown?",
    "fw?",
    "hasBtnBg?",
    "odooControlPanelSwitchStyle?",
    "thread?",
];

class Action extends Component {
    static props = ["action", "group", "isFirstInGroup?", "isLastInGroup?", ...actionListProps];
    static defaultProps = { fw: true };
    static components = { Action, DropdownItem };
    static template = "mail.Action";

    get ActionList() {
        return ActionList;
    }

    get Dropdown() {
        if (this.env.inDiscussCallView?.isPip) {
            return CallDropdown;
        }
        return Dropdown;
    }

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.attClassObjectToString = attClassObjectToString;
        if (this.props.action.definition?.isMoreAction) {
            this.dropdownState = useDropdownState();
            useEffect(
                () => {
                    this.props.action.definition.isActive = this.dropdownState.isOpen;
                },
                () => [this.dropdownState?.isOpen]
            );
            onWillUnmount(() => {
                this.props.action.definition.isActive = false;
            });
        }
    }

    get action() {
        return this.props.action;
    }

    get groupSize() {
        return this.props.group.length;
    }

    get hasBtnBg() {
        return this.props.odooControlPanelSwitchStyle || this.props.hasBtnBg;
    }

    onSelected(action, ev) {
        action.onSelected?.(ev);
        this.env.inCallDropdown?.close();
    }
}

export class ActionList extends Component {
    static components = { Action };
    static props = ["actions", "groupClass?", ...actionListProps];
    static template = "mail.ActionList";

    getActionProps(action, group, { isFirstInGroup, isLastInGroup } = {}) {
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
        };
    }

    setup() {
        super.setup();
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
