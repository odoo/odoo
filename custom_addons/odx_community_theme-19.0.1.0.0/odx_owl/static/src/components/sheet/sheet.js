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

function resolveSheetSide(side, dir) {
    if (side === "start") {
        return isRtlDirection(dir) ? "right" : "left";
    }
    if (side === "end") {
        return isRtlDirection(dir) ? "left" : "right";
    }
    return side || "right";
}

export class Sheet extends Component {
    static template = "odx_owl.Sheet";
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
        onEscapeKeyDown: { type: Function, optional: true },
        onInteractOutside: { type: Function, optional: true },
        onOpenChange: { type: Function, optional: true },
        onPointerDownOutside: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        showClose: { type: Boolean, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        closeOnEscape: true,
        closeOnOverlay: true,
        contentClass: "",
        defaultOpen: false,
        showClose: true,
        side: "right",
    };

    setup() {
        const self = this;
        this.state = useState({
            open: this.props.open ?? this.props.defaultOpen,
        });
        this.handleOpenChange = (open) => this.setOpen(open);

        useChildSubEnv({
            odxSheet: {
                get dir() {
                    return self.direction;
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

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get resolvedSide() {
        return resolveSheetSide(this.props.side, this.direction);
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

export class SheetOverlay extends Component {
    static template = "odx_owl.SheetOverlay";
    static components = { DialogOverlay };
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-sheet__overlay", this.props.className);
    }
}

export class SheetContent extends Component {
    static template = "odx_owl.SheetContent";
    static components = {
        DialogClose,
        DialogContent,
    };
    static props = {
        className: { type: String, optional: true },
        dir: { type: String, optional: true },
        showClose: { type: Boolean, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        showClose: true,
        side: "right",
        tag: "section",
    };

    get classes() {
        return cn(
            "odx-sheet__content",
            `odx-sheet__content--${this.resolvedSide}`,
            this.props.className
        );
    }

    get direction() {
        return resolveDirection(this.props.dir || this.env.odxSheet?.dir);
    }

    get resolvedSide() {
        return resolveSheetSide(this.props.side, this.direction);
    }
}

export class SheetClose extends Component {
    static template = "odx_owl.SheetClose";
    static components = { DialogClose };
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Close sheet",
        className: "",
        type: "button",
    };

    get classes() {
        return cn("odx-sheet__close", this.props.className);
    }
}

export class SheetTrigger extends Component {
    static template = "odx_owl.SheetTrigger";
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
        return cn("odx-sheet__trigger", this.props.className);
    }
}

export class SheetHeader extends Component {
    static template = "odx_owl.SheetHeader";
    static components = { DialogHeader };
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-sheet__header", this.props.className);
    }
}

export class SheetFooter extends Component {
    static template = "odx_owl.SheetFooter";
    static components = { DialogFooter };
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-sheet__footer", this.props.className);
    }
}

export class SheetTitle extends Component {
    static template = "odx_owl.SheetTitle";
    static components = { DialogTitle };
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "h2",
        text: "",
    };

    get classes() {
        return cn("odx-sheet__title", this.props.className);
    }
}

export class SheetDescription extends Component {
    static template = "odx_owl.SheetDescription";
    static components = { DialogDescription };
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

    get classes() {
        return cn("odx-sheet__description", this.props.className);
    }
}

Sheet.components = {
    Dialog,
    SheetContent,
    SheetDescription,
    SheetHeader,
    SheetOverlay,
    SheetTitle,
};
