/** @odoo-module **/

import {
    Component,
    onWillUpdateProps,
    useChildSubEnv,
    useState,
} from "@odoo/owl";
import { Button } from "@odx_owl/components/button/button";
import {
    Dialog,
    DialogContent,
    DialogDescription,
    DialogFooter,
    DialogHeader,
    DialogOverlay,
    DialogTitle,
} from "@odx_owl/components/dialog/dialog";
import { cn } from "@odx_owl/core/utils/cn";

export class AlertDialogTrigger extends Component {
    static template = "odx_owl.AlertDialogTrigger";
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
        return cn("odx-alert-dialog__trigger", this.props.className);
    }
}

export class AlertDialogOverlay extends Component {
    static template = "odx_owl.AlertDialogOverlay";
    static components = { DialogOverlay };
    static props = {
        className: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get classes() {
        return cn("odx-alert-dialog__overlay", this.props.className);
    }
}

export class AlertDialogContent extends Component {
    static template = "odx_owl.AlertDialogContent";
    static components = { DialogContent };
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "section",
    };

    get classes() {
        return cn("odx-alert-dialog__content", this.props.className);
    }
}

export class AlertDialogHeader extends Component {
    static template = "odx_owl.AlertDialogHeader";
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

export class AlertDialogFooter extends Component {
    static template = "odx_owl.AlertDialogFooter";
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

export class AlertDialogTitle extends Component {
    static template = "odx_owl.AlertDialogTitle";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn("odx-dialog__title", this.props.className);
    }
}

export class AlertDialogDescription extends Component {
    static template = "odx_owl.AlertDialogDescription";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        text: "",
    };

    get classes() {
        return cn("odx-dialog__description", this.props.className);
    }
}

class AlertDialogButton extends Component {
    static components = { Button };
    static props = {
        className: { type: String, optional: true },
        label: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        label: "",
    };

    setup() {
        this.handleAction = () => this.onAction();
    }

    async runBeforeAction() {
        return this.props.onClick?.();
    }
}

export class AlertDialogCancel extends AlertDialogButton {
    static template = "odx_owl.AlertDialogCancel";
    static defaultProps = {
        ...AlertDialogButton.defaultProps,
        label: "Cancel",
        variant: "outline",
    };

    async onAction() {
        const result = await this.runBeforeAction();
        if (result === false) {
            return;
        }
        await this.env.odxAlertDialog?.cancel?.();
    }
}

export class AlertDialogAction extends AlertDialogButton {
    static template = "odx_owl.AlertDialogAction";
    static defaultProps = {
        ...AlertDialogButton.defaultProps,
        label: "Continue",
        variant: "destructive",
    };

    async onAction() {
        const result = await this.runBeforeAction();
        if (result === false) {
            return;
        }
        await this.env.odxAlertDialog?.confirm?.();
    }
}

export class AlertDialog extends Component {
    static template = "odx_owl.AlertDialog";
    static components = {
        AlertDialogAction,
        AlertDialogCancel,
        AlertDialogContent,
        AlertDialogDescription,
        AlertDialogFooter,
        AlertDialogHeader,
        AlertDialogOverlay,
        AlertDialogTitle,
        Dialog,
    };
    static props = {
        cancelLabel: { type: String, optional: true },
        cancelVariant: { type: String, optional: true },
        className: { type: String, optional: true },
        closeOnEscape: { type: Boolean, optional: true },
        confirmLabel: { type: String, optional: true },
        confirmVariant: { type: String, optional: true },
        contentClass: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        description: { type: String, optional: true },
        onCancel: { type: Function, optional: true },
        onConfirm: { type: Function, optional: true },
        onEscapeKeyDown: { type: Function, optional: true },
        onInteractOutside: { type: Function, optional: true },
        onOpenChange: { type: Function, optional: true },
        onPointerDownOutside: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        title: { type: String, optional: true },
    };
    static defaultProps = {
        cancelLabel: "Cancel",
        cancelVariant: "outline",
        className: "",
        closeOnEscape: true,
        confirmLabel: "Continue",
        confirmVariant: "destructive",
        contentClass: "",
        defaultOpen: false,
    };

    setup() {
        const self = this;
        this.state = useState({
            open: this.props.open ?? this.props.defaultOpen,
        });
        this.handleOpenChange = (open) => this.setOpen(open);

        useChildSubEnv({
            odxAlertDialog: {
                cancel: () => self.cancel(),
                confirm: () => self.confirm(),
                get isOpen() {
                    return self.isOpen;
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

    get hasHeaderSlot() {
        return Boolean(this.props.slots?.header);
    }

    get hasHeader() {
        return Boolean(this.props.title || this.props.description || this.props.slots?.header);
    }

    get hasFooterSlot() {
        return Boolean(this.props.slots?.footer);
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

    async confirm() {
        const result = await this.props.onConfirm?.();
        if (result !== false) {
            this.setOpen(false);
        }
    }

    async cancel() {
        const result = await this.props.onCancel?.();
        if (result !== false) {
            this.setOpen(false);
        }
    }
}

AlertDialogAction.components = { Button };
AlertDialogCancel.components = { Button };
AlertDialogContent.components = { DialogContent };
AlertDialogDescription.components = { DialogDescription };
AlertDialogFooter.components = { DialogFooter };
AlertDialogHeader.components = { DialogHeader };
AlertDialogOverlay.components = { DialogOverlay };
AlertDialogTitle.components = { DialogTitle };
