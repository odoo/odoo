import { attClassObjectToString } from "@mail/utils/common/format";
import { Component, t, xml } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { Action as ActionModel } from "@mail/core/common/action";

/**
 * Base class holding what ActionButton and ActionDropdown have in common.
 * This component should not be used directly: subcomponents (e.g. ActionButton,
 * ActionDropdown) override `static template` with their own.
 */
export class ActionBase extends Component {
    static template = xml`<div/>`;
    static propsSchema = {
        action: t.instanceOf(ActionModel),
        attrs: t.object(),
        isInlineCircleButton: t.boolean(),
        fw: t.boolean().optional(),
        isFirstInGroup: t.boolean().optional(),
        isLastInGroup: t.boolean().optional(),
        hasBtnBg: t.boolean().optional(),
        odooControlPanelSwitchStyle: t.boolean().optional(),
        onSelected: t.function(),
    };

    setup() {
        super.setup();
        this.store = useService("mail.store");
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

    /** Position of the button within its action group. */
    get positionClass() {
        return {
            "o-first": this.props.isFirstInGroup,
            "o-last": this.props.isLastInGroup,
        };
    }

    /** Active/tag-based color classes. */
    get colorClass() {
        return {
            active: this.action.isActive,
            "o-odooControlPanelSwitchStyle": this.props.odooControlPanelSwitchStyle,
            "o-hasBtnBg": this.hasBtnBg,
            "bg-secondary":
                this.action.isActive &&
                !this.action.btnVariant &&
                !this.action.tags.includes("SUCCESS"),
            "btn-secondary": !this.action.btnVariant && !this.action.tags.includes("SUCCESS"),
            "btn-success": this.action.tags.includes("SUCCESS"),
        };
    }

    get darkThemeClass() {
        return {
            "o-text-white o-simulateDarkTheme": this.store.shouldSimulateDarkTheme(this),
            "bg-transparent": this.store.shouldSimulateDarkTheme(this) && !this.hasBtnBg,
            "o-inDiscussCall":
                this.env?.inDiscussCallView ||
                this.env?.inCallInvitation ||
                this.env.isDiscussPipBanner ||
                this.env?.inWelcomePage,
        };
    }

    /** Extra classes requested by the action itself. */
    get actionSpecificClass() {
        return {
            [this.action.btnClass ?? ""]: true,
            [this.action.btnVariant]: true,
            [this.action.tagClassNames]: true,
        };
    }

    /** Class naming this component's root element, meant to be overridden by subclasses. */
    get btnRootClass() {
        return "";
    }

    get classObj() {
        return {
            ...this.positionClass,
            ...this.colorClass,
            ...this.darkThemeClass,
            ...this.actionSpecificClass,
            [this.btnRootClass]: Boolean(this.btnRootClass),
        };
    }

    get btnClass() {
        return attClassObjectToString(this.classObj);
    }
}
