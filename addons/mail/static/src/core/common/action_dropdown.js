import { attClassObjectToString } from "@mail/utils/common/format";
import { Component } from "@odoo/owl";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useService } from "@web/core/utils/hooks";

export class ActionDropdown extends Component {
    static template = "mail.ActionDropdown";
    static components = { DropdownItem };
    static props = [
        "action",
        "attrs",
        "isInlineCircleButton",
        "inMeetingViewCallButtonsFullscreen",
        "fw?",
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
        return attClassObjectToString({
            "o-first": this.props.isFirstInGroup,
            "o-last": this.props.isLastInGroup,
            active: action.isActive,
            "o-odooControlPanelSwitchStyle": this.props.odooControlPanelSwitchStyle,
            "o-hasBtnBg": this.hasBtnBg,
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
            "text-start": !this.ui.isSmall,
            "px-1 py-2": this.props.inMeetingViewCallButtonsFullscreen,
            "px-3 py-2": this.ui.isSmall,
            "px-2 py-1": !this.ui.isSmall,
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
