import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, t, useProps } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Action as ActionModel } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";

export const actionButtonProps = ["inline?", "dropdown?", "fw?"];

export const actionButtonPropsSchema = {
    dropdown: t.boolean().optional(),
    fw: t.boolean().optional(true),
    inline: t.boolean().optional(),
};

/**
 * Renders the button/dropdown-item chrome for every action: core button
 * classes, icon/name content, badge, hotkey wiring. This is the single
 * generic renderer used by {@link Action} for every context - every button
 * looks the same regardless of where it's used or what the action is. The
 * only styling variation left is structural, not contextual: whether it
 * renders inline or as a block, and whether it renders as a plain button or
 * a dropdown item. An action that needs genuinely bespoke rendering instead
 * reaches for
 * `action.component` (@see Action in "@mail/core/common/action"), which
 * bypasses this chrome entirely.
 */
export class ActionButton extends Component {
    static template = "mail.ActionButton";
    static components = { DropdownItem };

    setup() {
        super.setup();
        this.props = useProps({
            action: t.instanceOf(ActionModel),
            style: t.string().optional(),
            ...actionButtonPropsSchema,
        });
        this.ui = useService("ui");
        this.attClassObjectToString = attClassObjectToString;
    }

    get action() {
        return this.props.action;
    }

    get paddingClass() {
        return this.attClassObjectToString({
            "o-p-0_5": this.props.inline,
            "px-3 py-2": this.props.dropdown && this.ui.isSmall,
            "px-2 py-1": this.props.dropdown && !this.ui.isSmall,
        });
    }

    get btnClass() {
        let cls = this.attClassObjectToString({
            "o-mail-ActionList-button btn btn-group-item btn-secondary position-relative": true,
            "o-inline": this.props.inline,
            "text-start": this.props.dropdown && !this.ui.isSmall,
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
