/** @odoo-module **/

import { Component } from "@odoo/owl";
import { Separator } from "@odx_owl/components/separator/separator";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const buttonGroupVariants = cva("odx-button-group", {
    variants: {
        orientation: {
            horizontal: "odx-button-group--horizontal",
            vertical: "odx-button-group--vertical",
        },
    },
    defaultVariants: {
        orientation: "horizontal",
    },
});

class ButtonGroupBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class ButtonGroup extends Component {
    static template = "odx_owl.ButtonGroup";
    static props = {
        className: { type: String, optional: true },
        orientation: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        orientation: "horizontal",
        tag: "div",
    };

    get classes() {
        return buttonGroupVariants({
            orientation: this.props.orientation,
            className: this.props.className,
        });
    }
}

export class ButtonGroupText extends ButtonGroupBase {
    static template = "odx_owl.ButtonGroupText";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
        text: "",
    };
    baseClass = "odx-button-group__text";
}

export class ButtonGroupSeparator extends Component {
    static template = "odx_owl.ButtonGroupSeparator";
    static components = {
        Separator,
    };
    static props = {
        className: { type: String, optional: true },
        decorative: { type: Boolean, optional: true },
        orientation: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        decorative: true,
        orientation: "vertical",
    };

    get classes() {
        return cn("odx-button-group__separator", this.props.className);
    }
}
