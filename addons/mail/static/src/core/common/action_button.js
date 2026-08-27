import { t, useProps } from "@odoo/owl";
import { ActionBase } from "@mail/core/common/action_base";

export class ActionButton extends ActionBase {
    static template = "mail.ActionButton";

    props = useProps({
        ...ActionBase.propsSchema,
        style: t.string().optional(),
    });

    get alignmentClass() {
        return {
            "d-flex align-items-center": this.props.isInlineCircleButton,
        };
    }

    get borderClass() {
        return {
            "border-0": !this.hasBtnBg && this.action.icon,
            "border-2": !this.hasBtnBg && !this.action.icon,
        };
    }

    get roundnessClass() {
        const isInlineCircleButton = this.props.isInlineCircleButton;
        return {
            "rounded-circle": isInlineCircleButton,
            "rounded-start-3": !isInlineCircleButton && this.props.isFirstInGroup,
            "rounded-end-3": !isInlineCircleButton && this.props.isLastInGroup,
        };
    }

    get marginClass() {
        return {
            "o-mx-0_5": !this.hasBtnBg && !this.action.icon,
        };
    }

    get paddingClass() {
        const isInlineCircleButton = this.props.isInlineCircleButton;
        return {
            "o-px-1_5 py-1":
                (this.hasBtnBg && !isInlineCircleButton && !this.env.inMeetingView) ||
                (!this.hasBtnBg && this.env.inComposer),
            "o-p-1_5":
                !this.env.inMeetingView &&
                this.hasBtnBg &&
                isInlineCircleButton &&
                !this.env.inChatWindow,
            "o-px-0_5": !this.env.inMeetingView && !this.hasBtnBg && !this.action.icon,
            "p-1": this.hasBtnBg && isInlineCircleButton && this.env.inChatWindow,
            "o-p-0_5": !this.env.inMeetingView && !this.hasBtnBg && !this.env.inComposer,
            "o-px-0_5 py-0": this.env.inMessage,
        };
    }

    get classObj() {
        return {
            ...super.classObj,
            ...this.alignmentClass,
            ...this.borderClass,
            ...this.roundnessClass,
            ...this.marginClass,
            ...this.paddingClass,
        };
    }
}
