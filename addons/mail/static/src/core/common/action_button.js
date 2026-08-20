import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, t, useProps } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { Action as ActionModel } from "@mail/core/common/action";
import { useService } from "@web/core/utils/hooks";

export const actionButtonProps = [
    "inline?",
    "dropdown?",
    "fw?",
    "hasBtnBg?",
    "odooControlPanelSwitchStyle?",
];

export const actionButtonPropsSchema = {
    dropdown: t.boolean().optional(),
    fw: t.boolean().optional(true),
    hasBtnBg: t.boolean().optional(),
    inline: t.boolean().optional(),
    odooControlPanelSwitchStyle: t.boolean().optional(),
};

/**
 * Renders the button/dropdown-item chrome shared by every action: core button
 * classes, icon/name content, badge, hotkey wiring. This is the "usual case"
 * renderer picked by {@link Action} whenever none of the more specific
 * contexts below apply.
 *
 * {@link ComposerActionButton}, {@link MessageActionButton} and
 * {@link CallSurfaceActionButton} extend this for the composer toolbar, the
 * message hover-toolbar, and call surfaces (call view, meeting, call
 * invitation, pip banner, welcome page) respectively: each owns only the
 * spacing/theming rules specific to its context instead of every context's
 * rules living together in one place.
 */
export class ActionButton extends Component {
    static template = "mail.ActionButton";
    static components = { DropdownItem };

    setup() {
        super.setup();
        this.props = useProps({
            action: t.instanceOf(ActionModel),
            isFirstInGroup: t.boolean().optional(),
            isLastInGroup: t.boolean().optional(),
            style: t.string().optional(),
            ...actionButtonPropsSchema,
        });
        this.store = useService("mail.store");
        this.ui = useService("ui");
        this.attClassObjectToString = attClassObjectToString;
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

    /** Whether the button renders as a plain circular icon button instead of a label pill. */
    get isInlineCircleButton() {
        if (!this.props.inline || !this.action.icon) {
            return false;
        }
        return this.action.tags.includes("JOIN_LEAVE_CALL") && !this.action.inlineName;
    }

    /**
     * Whether this is a call-control button shown enlarged in a fullscreen meeting.
     * Only ever true for {@link CallSurfaceActionButton}: composer- and message-owned
     * buttons are always excluded (they're either not in a meeting, or nested through
     * an ActionPanel like the in-call chat panel, both of which rule this out).
     */
    get isFullscreenCallButton() {
        return false;
    }

    get paddingClass() {
        return this.attClassObjectToString({
            "px-1 py-2": this.isFullscreenCallButton,
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
            "px-3 py-2": this.props.dropdown && this.ui.isSmall,
            "px-2 py-1": this.props.dropdown && !this.ui.isSmall,
        });
    }

    /**
     * Dark-theme simulation and the discuss-call tint. Kept shared (not overridden per
     * variant): `o-inDiscussCall` can apply even to a composer/message button nested
     * inside a call surface (e.g. the in-call chat panel), so it must stay driven by
     * live env reads rather than by which chrome variant is rendering.
     */
    get darkThemeClass() {
        return this.attClassObjectToString({
            "o-text-white o-simulateDarkTheme": this.store.shouldSimulateDarkTheme(this),
            "bg-transparent": this.store.shouldSimulateDarkTheme(this) && !this.hasBtnBg,
            "o-inDiscussCall":
                this.env?.inDiscussCallView ||
                this.env?.inCallInvitation ||
                this.env.isDiscussPipBanner ||
                this.env?.inWelcomePage,
        });
    }

    get btnClass() {
        let cls = this.attClassObjectToString({
            "o-mail-ActionList-button btn btn-group-item position-relative": true,
            "o-first": this.props.isFirstInGroup,
            "o-last": this.props.isLastInGroup,
            active: this.action.isActive,
            "o-odooControlPanelSwitchStyle": this.props.odooControlPanelSwitchStyle,
            "o-hasBtnBg": this.hasBtnBg,
            "o-inline": this.props.inline,
            "bg-secondary":
                this.action.isActive &&
                !this.action.tags.includes("PRIMARY") &&
                !this.action.tags.includes("DANGER") &&
                !this.action.tags.includes("SUCCESS"),
            "btn-secondary":
                !this.action.tags.includes("PRIMARY") &&
                !this.action.tags.includes("DANGER") &&
                !this.action.tags.includes("SUCCESS"),
            "btn-primary": this.action.tags.includes("PRIMARY"),
            "btn-danger": this.action.tags.includes("DANGER"),
            "btn-success": this.action.tags.includes("SUCCESS"),
        });
        cls = this.attClassObjectToString({
            [cls]: true,
            "d-flex align-items-center": this.props.inline && this.isInlineCircleButton,
            "text-start": this.props.dropdown && !this.ui.isSmall,
        });
        cls = this.attClassObjectToString({
            [cls]: true,
            "border-0": this.props.inline && !this.hasBtnBg && this.action.icon,
            "border-2": this.props.inline && !this.hasBtnBg && !this.action.icon,
        });
        cls = this.attClassObjectToString({
            [cls]: true,
            "rounded-circle": this.props.inline && this.isInlineCircleButton,
            "rounded-start-3":
                this.props.inline && !this.isInlineCircleButton && this.props.isFirstInGroup,
            "rounded-end-3":
                this.props.inline && !this.isInlineCircleButton && this.props.isLastInGroup,
        });
        cls = this.attClassObjectToString({
            [cls]: true,
            "o-mx-0_5": this.props.inline && !this.hasBtnBg && !this.action.icon,
        });
        cls = this.attClassObjectToString({ [cls]: true, [this.paddingClass]: true });
        cls = this.attClassObjectToString({ [cls]: true, [this.darkThemeClass]: true });
        cls = this.attClassObjectToString({
            [cls]: true,
            [this.action.btnClass ?? ""]: true,
            [this.action.tagClassNames]: true,
        });
        return cls;
    }

    onSelected(action, ev) {
        action.onSelected?.(ev);
        this.env.inCallDropdown?.close();
    }
}
