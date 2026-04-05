/** @odoo-module **/

import { Component } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const itemVariants = cva("odx-item", {
    variants: {
        size: {
            default: "odx-item--size-default",
            sm: "odx-item--size-sm",
        },
        variant: {
            default: "odx-item--default",
            outline: "odx-item--outline",
            muted: "odx-item--muted",
        },
    },
    defaultVariants: {
        size: "default",
        variant: "default",
    },
});

export const itemMediaVariants = cva("odx-item__media", {
    variants: {
        variant: {
            default: "odx-item__media--default",
            icon: "odx-item__media--icon",
            image: "odx-item__media--image",
        },
    },
    defaultVariants: {
        variant: "default",
    },
});

class ItemBase extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class ItemGroup extends ItemBase {
    static template = "odx_owl.ItemGroup";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-item-group";
}

export class ItemSeparator extends ItemBase {
    static template = "odx_owl.ItemSeparator";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-item-separator";
}

export class Item extends Component {
    static template = "odx_owl.Item";
    static props = {
        className: { type: String, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        tabindex: { type: Number, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        size: "default",
        tag: "div",
        variant: "default",
    };

    get classes() {
        return itemVariants({
            size: this.props.size,
            variant: this.props.variant,
            className: this.props.className,
        });
    }
}

export class ItemMedia extends Component {
    static template = "odx_owl.ItemMedia";
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
        return itemMediaVariants({
            variant: this.props.variant,
            className: this.props.className,
        });
    }
}

export class ItemContent extends ItemBase {
    static template = "odx_owl.ItemContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-item__content";
}

export class ItemTitle extends ItemBase {
    static template = "odx_owl.ItemTitle";
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
    baseClass = "odx-item__title";
}

export class ItemDescription extends ItemBase {
    static template = "odx_owl.ItemDescription";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "p",
        text: "",
    };
    baseClass = "odx-item__description";
}

export class ItemActions extends ItemBase {
    static template = "odx_owl.ItemActions";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };
    baseClass = "odx-item__actions";
}

export class ItemHeader extends ItemActions {
    static template = "odx_owl.ItemHeader";
    baseClass = "odx-item__header";
}

export class ItemFooter extends ItemActions {
    static template = "odx_owl.ItemFooter";
    baseClass = "odx-item__footer";
}
