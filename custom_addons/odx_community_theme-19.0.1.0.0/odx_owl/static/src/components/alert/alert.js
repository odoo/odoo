/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const alertVariants = cva("odx-alert", {
    variants: {
        variant: {
            default: "odx-alert--default",
            destructive: "odx-alert--destructive",
        },
    },
    defaultVariants: {
        variant: "default",
    },
});

export class Alert extends Component {
    static template = "odx_owl.Alert";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        variant: "default",
    };

    get classes() {
        return alertVariants({
            variant: this.props.variant,
            className: this.props.className,
        });
    }
}

export class AlertTitle extends Component {
    static template = "odx_owl.AlertTitle";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-alert__title", this.props.className);
    }
}

export class AlertDescription extends Component {
    static template = "odx_owl.AlertDescription";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-alert__description", this.props.className);
    }
}
