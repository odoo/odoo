import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, t, useProps } from "@odoo/owl";
import { Action as ActionModel } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";

/**
 * Renders the button chrome for an action: core button classes, icon/name
 * content, badge, hotkey wiring. This is the generic renderer used by
 * {@link Action} for actions not shown inside another dropdown's menu.
 * @see ActionDropdown for the same chrome rendered as a `DropdownItem`,
 * used when `props.dropdown` is set. An action that needs genuinely bespoke
 * rendering instead reaches for `action.component` (@see Action in
 * "@mail/core/common/action"), which bypasses this chrome entirely.
 */
export class ActionButton extends Component {
    static template = "mail.ActionButton";

    setup() {
        super.setup();
        this.props = useProps({
            action: t.instanceOf(ActionModel),
            style: t.string().optional(),
            dropdown: t.boolean().optional(),
            inline: t.boolean().optional(),
            rounded: t.boolean().optional(),
            variant: t.function([], t.string()).optional(() => () => "btn-secondary"),
        });
        this.ui = useService("ui");
        this.attClassObjectToString = attClassObjectToString;
    }

    get action() {
        return this.props.action;
    }

    get paddingClass() {
        return this.attClassObjectToString({
            "px-3 py-2": this.props.dropdown && this.ui.isSmall,
            "px-2 py-1": this.props.dropdown && !this.ui.isSmall,
        });
    }

    get btnClass() {
        let cls = this.attClassObjectToString({
            "o-mail-ActionList-button btn btn-group-item position-relative": true,
            [this.props.variant()]: true,
            "o-inline": this.props.inline,
            "text-start": this.props.dropdown && !this.ui.isSmall,
            "rounded-circle d-flex align-items-center justify-content-center": this.props.rounded,
        });
        cls = this.attClassObjectToString({ [cls]: true, [this.paddingClass]: true });
        cls = this.attClassObjectToString({
            [cls]: true,
            [this.action.btnClass ?? ""]: true,
        });
        return cls;
    }

    onSelected(action, ev) {
        action.onSelected?.(ev);
        this.env.inCallDropdown?.close();
    }
}
