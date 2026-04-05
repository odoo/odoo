/** @odoo-module **/

import {
    Component,
    onMounted,
    onWillDestroy,
    onWillUpdateProps,
    useChildSubEnv,
    useEffect,
    useExternalListener,
    useState,
} from "@odoo/owl";
import { useActiveElement } from "@web/core/ui/ui_service";
import { cva } from "@odx_owl/core/utils/variants";
import { cn } from "@odx_owl/core/utils/cn";
import { nextId } from "@odx_owl/core/utils/ids";

const dialogContentVariants = cva("odx-dialog__content", {
    variants: {
        size: {
            sm: "odx-dialog__content--sm",
            default: "odx-dialog__content--default",
            lg: "odx-dialog__content--lg",
            xl: "odx-dialog__content--xl",
            full: "odx-dialog__content--full",
        },
    },
    defaultVariants: {
        size: "default",
    },
});

function createDismissibleEvent(originalEvent) {
    return {
        defaultPrevented: false,
        originalEvent,
        preventDefault() {
            this.defaultPrevented = true;
            originalEvent?.preventDefault?.();
        },
    };
}

export class DialogHeader extends Component {
    static template = "odx_owl.DialogHeader";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-dialog__header", this.props.className);
    }
}

export class DialogFooter extends Component {
    static template = "odx_owl.DialogFooter";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-dialog__footer", this.props.className);
    }
}

export class DialogTitle extends Component {
    static template = "odx_owl.DialogTitle";
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

    setup() {
        onMounted(() => this.env.odxDialog?.registerTitle?.());
        onWillDestroy(() => this.env.odxDialog?.unregisterTitle?.());
    }

    get classes() {
        return cn("odx-dialog__title", this.props.className);
    }

    get id() {
        return this.env.odxDialog?.titleId;
    }
}

export class DialogDescription extends Component {
    static template = "odx_owl.DialogDescription";
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

    setup() {
        onMounted(() => this.env.odxDialog?.registerDescription?.());
        onWillDestroy(() => this.env.odxDialog?.unregisterDescription?.());
    }

    get classes() {
        return cn("odx-dialog__description", this.props.className);
    }

    get id() {
        return this.env.odxDialog?.descriptionId;
    }
}

export class DialogClose extends Component {
    static template = "odx_owl.DialogClose";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Close dialog",
        className: "",
        type: "button",
    };

    get classes() {
        return cn("odx-dialog__close", this.props.className);
    }

    onClick(ev) {
        this.props.onClick?.(ev);
        if (!ev.defaultPrevented) {
            this.env.odxDialog?.close?.();
        }
    }
}

export class DialogTrigger extends Component {
    static template = "odx_owl.DialogTrigger";
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
        return cn("odx-dialog__trigger-content", this.props.className);
    }

    onClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.env.odxDialog?.open?.();
    }
}

export class DialogOverlay extends Component {
    static template = "odx_owl.DialogOverlay";
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn(this.env.odxDialog?.overlayClasses, this.props.className);
    }

    onClick(ev) {
        this.env.odxDialog?.onOverlayClick?.(ev);
    }

    onPointerDown(ev) {
        this.env.odxDialog?.onOverlayPointerDown?.(ev);
    }
}

export class DialogContent extends Component {
    static template = "odx_owl.DialogContent";
    static props = {
        className: { type: String, optional: true },
        dir: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "section",
    };

    get classes() {
        return cn(this.env.odxDialog?.contentClasses, this.props.className);
    }

    get role() {
        return this.env.odxDialog?.role;
    }

    get titleId() {
        return this.env.odxDialog?.hasTitle ? this.env.odxDialog?.titleId : undefined;
    }

    get descriptionId() {
        return this.env.odxDialog?.hasDescription ? this.env.odxDialog?.descriptionId : undefined;
    }
}

export class Dialog extends Component {
    static template = "odx_owl.Dialog";
    static components = {
        DialogClose,
        DialogContent,
        DialogDescription,
        DialogFooter,
        DialogHeader,
        DialogOverlay,
        DialogTitle,
        DialogTrigger,
    };
    static props = {
        className: { type: String, optional: true },
        closeOnEscape: { type: Boolean, optional: true },
        closeOnOverlay: { type: Boolean, optional: true },
        contentClass: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        description: { type: String, optional: true },
        onEscapeKeyDown: { type: Function, optional: true },
        onInteractOutside: { type: Function, optional: true },
        onOpenChange: { type: Function, optional: true },
        onPointerDownOutside: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        overlayClass: { type: String, optional: true },
        role: { type: String, optional: true },
        showClose: { type: Boolean, optional: true },
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
        overlayClass: "",
        role: "dialog",
        showClose: true,
        size: "default",
    };

    setup() {
        const self = this;
        this.overlayPointerAllowed = true;
        this.state = useState({
            descriptionCount: 0,
            open: this.props.open ?? this.props.defaultOpen,
            titleCount: 0,
            titleId: nextId("odx-dialog-title"),
            descriptionId: nextId("odx-dialog-description"),
        });

        useChildSubEnv({
            odxDialog: {
                close: () => self.closeDialog(),
                get contentClasses() {
                    return self.contentClasses;
                },
                get descriptionId() {
                    return self.state.descriptionId;
                },
                get hasDescription() {
                    return self.hasDescription;
                },
                get hasTitle() {
                    return self.hasTitle;
                },
                open: () => self.openDialog(),
                onOverlayClick: (ev) => self.onOverlayClick(ev),
                onOverlayPointerDown: (ev) => self.onOverlayPointerDown(ev),
                get overlayClasses() {
                    return self.overlayClasses;
                },
                registerDescription: () => self.registerDescription(),
                registerTitle: () => self.registerTitle(),
                get role() {
                    return self.props.role;
                },
                get titleId() {
                    return self.state.titleId;
                },
                unregisterDescription: () => self.unregisterDescription(),
                unregisterTitle: () => self.unregisterTitle(),
            },
        });

        useActiveElement("portalRef");
        useExternalListener(window, "keydown", (ev) => this.onWindowKeydown(ev));

        useEffect(
            () => {
                if (!this.isOpen) {
                    return;
                }
                document.body.classList.add("odx-dialog-open");
                return () => document.body.classList.remove("odx-dialog-open");
            },
            () => [this.isOpen]
        );

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
        return Boolean(
            this.props.title ||
                this.props.description ||
                this.props.slots?.header ||
                this.hasRegisteredTitle ||
                this.hasRegisteredDescription
        );
    }

    get hasRegisteredTitle() {
        return this.state.titleCount > 0;
    }

    get hasRegisteredDescription() {
        return this.state.descriptionCount > 0;
    }

    get hasTitle() {
        return Boolean(this.props.title || this.hasRegisteredTitle);
    }

    get hasDescription() {
        return Boolean(this.props.description || this.hasRegisteredDescription);
    }

    get contentClasses() {
        return dialogContentVariants({
            size: this.props.size,
            className: cn(this.props.className, this.props.contentClass),
        });
    }

    get overlayClasses() {
        return cn("odx-dialog__overlay", this.props.overlayClass);
    }

    registerTitle() {
        this.state.titleCount += 1;
    }

    unregisterTitle() {
        this.state.titleCount = Math.max(0, this.state.titleCount - 1);
    }

    registerDescription() {
        this.state.descriptionCount += 1;
    }

    unregisterDescription() {
        this.state.descriptionCount = Math.max(0, this.state.descriptionCount - 1);
    }

    openDialog() {
        this.setOpen(true);
    }

    closeDialog() {
        this.setOpen(false);
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        if (open) {
            this.overlayPointerAllowed = true;
        }
        this.props.onOpenChange?.(open);
    }

    createDismissibleEvent(originalEvent) {
        return createDismissibleEvent(originalEvent);
    }

    onOverlayPointerDown(ev) {
        if (ev.target !== ev.currentTarget) {
            return;
        }
        const dismissEvent = this.createDismissibleEvent(ev);
        this.props.onPointerDownOutside?.(dismissEvent);
        this.overlayPointerAllowed = !dismissEvent.defaultPrevented;
    }

    onOverlayClick(ev) {
        if (ev.target !== ev.currentTarget) {
            return;
        }
        if (!this.overlayPointerAllowed) {
            this.overlayPointerAllowed = true;
            return;
        }
        const dismissEvent = this.createDismissibleEvent(ev);
        this.props.onInteractOutside?.(dismissEvent);
        if (!dismissEvent.defaultPrevented && this.props.closeOnOverlay) {
            this.closeDialog();
        }
        this.overlayPointerAllowed = true;
    }

    onWindowKeydown(ev) {
        if (!this.isOpen || ev.key !== "Escape") {
            return;
        }
        const dismissEvent = this.createDismissibleEvent(ev);
        this.props.onEscapeKeyDown?.(dismissEvent);
        if (!dismissEvent.defaultPrevented && this.props.closeOnEscape) {
            ev.preventDefault();
            this.closeDialog();
        }
    }
}
