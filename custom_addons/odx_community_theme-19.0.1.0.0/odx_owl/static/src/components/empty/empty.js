/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const emptyMediaVariants = cva("odx-empty__media", {
    variants: {
        variant: {
            default: "odx-empty__media--default",
            icon: "odx-empty__media--icon",
        },
    },
    defaultVariants: {
        variant: "default",
    },
});

class EmptyBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class Empty extends EmptyBase {
    static template = "odx_owl.Empty";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-empty";
}

export class EmptyHeader extends EmptyBase {
    static template = "odx_owl.EmptyHeader";
    static props = Empty.props;
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-empty__header";
}

export class EmptyTitle extends EmptyBase {
    static template = "odx_owl.EmptyTitle";
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
    baseClass = "odx-empty__title";
}

export class EmptyDescription extends EmptyTitle {
    static template = "odx_owl.EmptyDescription";
    static defaultProps = {
        className: "",
        tag: "p",
        text: "",
    };
    baseClass = "odx-empty__description";
}

export class EmptyContent extends EmptyBase {
    static template = "odx_owl.EmptyContent";
    static props = Empty.props;
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-empty__content";
}

export class EmptyMedia extends Component {
    static template = "odx_owl.EmptyMedia";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
        variant: "default",
    };

    get classes() {
        return emptyMediaVariants({
            variant: this.props.variant,
            className: this.props.className,
        });
    }
}
