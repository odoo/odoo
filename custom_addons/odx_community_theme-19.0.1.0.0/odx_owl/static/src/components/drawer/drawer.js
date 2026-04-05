/** @odoo-module **/

import { Component, onWillUpdateProps, useChildSubEnv, useState } from "@odoo/owl";
import {
    Dialog,
    DialogClose,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogOverlay,
    DialogTitle,
} from "@odx_owl/components/dialog/dialog";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { cva } from "@odx_owl/core/utils/variants";

function resolveDrawerDirection(direction, dir) {
    if (direction === "start") {
        return isRtlDirection(dir) ? "right" : "left";
    }
    if (direction === "end") {
        return isRtlDirection(dir) ? "left" : "right";
    }
    return direction || "bottom";
}

const drawerContentVariants = cva("odx-drawer__content", {
    variants: {
        direction: {
            top: "odx-drawer__content--top",
            bottom: "odx-drawer__content--bottom",
            left: "odx-drawer__content--left",
            right: "odx-drawer__content--right",
        },
        size: {
            sm: "odx-drawer__content--sm",
            default: "odx-drawer__content--default",
            lg: "odx-drawer__content--lg",
        },
    },
    defaultVariants: {
        direction: "bottom",
        size: "default",
    },
});

export class Drawer extends Component {
    static template = "odx_owl.Drawer";
    static components = {
        Dialog,
    };
    static props = {
        className: { type: String, optional: true },
        closeOnEscape: { type: Boolean, optional: true },
        closeOnOverlay: { type: Boolean, optional: true },
        contentClass: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        description: { type: String, optional: true },
        dir: { type: String, optional: true },
        direction: { type: String, optional: true },
        onEscapeKeyDown: { type: Function, optional: true },
        onInteractOutside: { type: Function, optional: true },
        onOpenChange: { type: Function, optional: true },
        onPointerDownOutside: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        showClose: { type: Boolean, optional: true },
        showHandle: { type: Boolean, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        closeOnEscape: true,
        closeOnOverlay: true,
        contentClass: "",
        defaultOpen: false,
        direction: "bottom",
        showClose: true,
        showHandle: true,
        size: "default",
    };

    setup() {
        const self = this;
        this.state = useState({
            open: this.props.open ?? this.props.defaultOpen,
        });
        this.handleOpenChange = (open) => this.setOpen(open);

        useChildSubEnv({
            odxDrawer: {
                get dir() {
                    return self.directionName;
                },
            },
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
        });
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get hasHeader() {
        return Boolean(this.props.title || this.props.description || this.props.slots?.header);
    }

    get directionName() {
        return resolveDirection(this.props.dir);
    }

    get resolvedDirection() {
        return resolveDrawerDirection(this.props.direction, this.directionName);
    }

    get panelClassName() {
        return cn(this.props.className, this.props.contentClass);
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        this.props.onOpenChange?.(open);
    }
}

export class DrawerOverlay extends Component {
    static template = "odx_owl.DrawerOverlay";
    static components = { DialogOverlay };
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-drawer__overlay", this.props.className);
    }
}

export class DrawerContent extends Component {
    static template = "odx_owl.DrawerContent";
    static components = {
        DialogClose,
        DialogContent,
    };
    static props = {
        className: { type: String, optional: true },
        dir: { type: String, optional: true },
        direction: { type: String, optional: true },
        showClose: { type: Boolean, optional: true },
        showHandle: { type: Boolean, optional: true },
        size: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        direction: "bottom",
        showClose: true,
        showHandle: true,
        size: "default",
        tag: "section",
    };

    get classes() {
        return drawerContentVariants({
            direction: this.resolvedDirection,
            size: this.props.size,
            className: this.props.className,
        });
    }

    get directionName() {
        return resolveDirection(this.props.dir || this.env.odxDrawer?.dir);
    }

    get resolvedDirection() {
        return resolveDrawerDirection(this.props.direction, this.directionName);
    }
}

export class DrawerClose extends Component {
    static template = "odx_owl.DrawerClose";
    static components = { DialogClose };
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Close drawer",
        className: "",
        type: "button",
    };

    get classes() {
        return cn("odx-drawer__close", this.props.className);
    }
}

export class DrawerTrigger extends Component {
    static template = "odx_owl.DrawerTrigger";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "span",
        text: "",
    };

    get classes() {
        return cn("odx-drawer__trigger", this.props.className);
    }
}

class DrawerSection extends Component {
    get classes() {
        return cn(this.baseClass, this.props.className);
    }
}

export class DrawerHeader extends DrawerSection {
    static template = "odx_owl.DrawerHeader";
    static components = { DialogHeader };
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-drawer__header";
}

export class DrawerFooter extends DrawerSection {
    static template = "odx_owl.DrawerFooter";
    static components = { DialogFooter };
    static props = DrawerHeader.props;
    static defaultProps = {
        className: "",
    };
    baseClass = "odx-drawer__footer";
}

export class DrawerTitle extends DrawerSection {
    static template = "odx_owl.DrawerTitle";
    static components = { DialogTitle };
    static props = {
        ...DrawerHeader.props,
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "h2",
        text: "",
    };
    baseClass = "odx-drawer__title";
}

export class DrawerDescription extends DrawerSection {
    static template = "odx_owl.DrawerDescription";
    static components = { DialogDescription };
    static props = {
        ...DrawerHeader.props,
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "p",
        text: "",
    };
    baseClass = "odx-drawer__description";
}

Drawer.components = {
    Dialog,
    DrawerContent,
    DrawerDescription,
    DrawerHeader,
    DrawerOverlay,
    DrawerTitle,
};
