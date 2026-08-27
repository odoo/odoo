import { attClassObjectToString } from "@mail/utils/common/format";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class ActionButton extends Component {
    static template = "mail.ActionButton";
    static props = [
        "action",
        "attrs",
        "style?",
        "isInlineCircleButton",
        "inMeetingViewCallButtonsFullscreen",
        "dropdown?",
        "fw?",
        "inline?",
        "isFirstInGroup?",
        "isLastInGroup?",
        "hasBtnBg?",
        "odooControlPanelSwitchStyle?",
        "onSelected",
    ];

    setup() {
        super.setup();
        this.store = useService("mail.store");
        this.ui = useService("ui");
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

    get btnClass() {
        const action = this.action;
        const isInlineCircleButton = this.props.isInlineCircleButton;
        return attClassObjectToString({
            "o-first": this.props.isFirstInGroup,
            "o-last": this.props.isLastInGroup,
            active: action.isActive,
            "o-odooControlPanelSwitchStyle": this.props.odooControlPanelSwitchStyle,
            "o-hasBtnBg": this.hasBtnBg,
            "o-inline": this.props.inline,
            "bg-secondary":
                action.isActive &&
                !action.tags.includes("PRIMARY") &&
                !action.tags.includes("DANGER") &&
                !action.tags.includes("SUCCESS"),
            "btn-secondary":
                !action.tags.includes("PRIMARY") &&
                !action.tags.includes("DANGER") &&
                !action.tags.includes("SUCCESS"),
            "btn-primary": action.tags.includes("PRIMARY"),
            "btn-danger": action.tags.includes("DANGER"),
            "btn-success": action.tags.includes("SUCCESS"),
            "d-flex align-items-center": this.props.inline && isInlineCircleButton,
            "text-start": this.props.dropdown && !this.ui.isSmall,
            "border-0": this.props.inline && !this.hasBtnBg && action.icon,
            "border-2": this.props.inline && !this.hasBtnBg && !action.icon,
            "rounded-circle": this.props.inline && isInlineCircleButton,
            "rounded-start-3":
                this.props.inline && !isInlineCircleButton && this.props.isFirstInGroup,
            "rounded-end-3": this.props.inline && !isInlineCircleButton && this.props.isLastInGroup,
            "o-mx-0_5": this.props.inline && !this.hasBtnBg && !action.icon,
            "px-1 py-2": this.props.inMeetingViewCallButtonsFullscreen,
            "o-px-1_5 py-1":
                this.props.inline &&
                ((this.hasBtnBg && !isInlineCircleButton && !this.env.inMeetingView) ||
                    (!this.hasBtnBg && this.env.inComposer)),
            "o-p-1_5":
                this.props.inline &&
                !this.env.inMeetingView &&
                this.hasBtnBg &&
                isInlineCircleButton &&
                !this.env.inChatWindow,
            "o-px-0_5":
                this.props.inline && !this.env.inMeetingView && !this.hasBtnBg && !action.icon,
            "p-1":
                this.props.inline && this.hasBtnBg && isInlineCircleButton && this.env.inChatWindow,
            "o-p-0_5":
                this.props.inline &&
                !this.env.inMeetingView &&
                !this.hasBtnBg &&
                !this.env.inComposer,
            "o-px-0_5 py-0": this.props.inline && this.env.inMessage,
            "px-3 py-2": this.props.dropdown && this.ui.isSmall,
            "px-2 py-1": this.props.dropdown && !this.ui.isSmall,
            "o-text-white o-simulateDarkTheme": this.store.shouldSimulateDarkTheme(this),
            "bg-transparent": this.store.shouldSimulateDarkTheme(this) && !this.hasBtnBg,
            "o-inDiscussCall":
                this.env?.inDiscussCallView ||
                this.env?.inCallInvitation ||
                this.env.isDiscussPipBanner ||
                this.env?.inWelcomePage,
            [action.btnClass ?? ""]: true,
            [action.tagClassNames]: true,
        });
    }
}
