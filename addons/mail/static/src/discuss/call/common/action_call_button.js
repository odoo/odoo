import { ActionButton } from "@mail/core/common/action_button";

/**
 * ActionButton variant for call-related actions, set as an action's `buttonComponent`. Always
 * rendered as an inline circle button, and carries the call-specific styling previously driven
 * by the `o-tag-JOIN_LEAVE_CALL` selectors (@see action_call_button.scss).
 */
export class ActionCallButton extends ActionButton {
    static template = "discuss.ActionCallButton";

    get btnRootClass() {
        return "o-mail-ActionCallButton";
    }

    /** A call button is a bare circular icon button unless it carries a text label. */
    get isInlineCircleButton() {
        return super.isInlineCircleButton || (Boolean(this.action.icon) && !this.action.label);
    }
}
