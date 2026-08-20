import { ActionButton } from "@mail/core/common/action_button";

/**
 * Chrome for actions rendered in a message's hover toolbar (`env.inMessage`).
 * Message buttons with an icon are always shown as circular icon buttons, and
 * get their own tight padding.
 */
export class MessageActionButton extends ActionButton {
    get isInlineCircleButton() {
        return this.props.inline && !!this.action.icon;
    }

    get paddingClass() {
        return this.attClassObjectToString({
            "o-px-1_5 py-1":
                this.props.inline &&
                this.hasBtnBg &&
                !this.isInlineCircleButton &&
                !this.env.inMeetingView,
            "o-p-1_5":
                this.props.inline &&
                !this.env.inMeetingView &&
                this.hasBtnBg &&
                this.isInlineCircleButton &&
                !this.env.inChatWindow,
            "o-px-0_5":
                this.props.inline && !this.env.inMeetingView && !this.hasBtnBg && !this.action.icon,
            "p-1":
                this.props.inline &&
                this.hasBtnBg &&
                this.isInlineCircleButton &&
                this.env.inChatWindow,
            "o-p-0_5": this.props.inline && !this.env.inMeetingView && !this.hasBtnBg,
            "o-px-0_5 py-0": this.props.inline,
            "px-3 py-2": this.props.dropdown && this.ui.isSmall,
            "px-2 py-1": this.props.dropdown && !this.ui.isSmall,
        });
    }
}
