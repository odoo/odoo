/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cva } from "@odx_owl/core/utils/variants";

export const badgeVariants = cva("odx-badge", {
    variants: {
        variant: {
            default: "odx-badge--default",
            secondary: "odx-badge--secondary",
            outline: "odx-badge--outline",
            destructive: "odx-badge--destructive",
        },
    },
    defaultVariants: {
        variant: "default",
    },
});

export class Badge extends Component {
    static template = "odx_owl.Badge";
    static props = {
        className: { type: String, optional: true },
        label: { type: String, optional: true },
        slots: { type: Object, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        variant: "default",
    };

    get classes() {
        return badgeVariants({
            variant: this.props.variant,
            className: this.props.className,
        });
    }
}
