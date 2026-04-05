/** @odoo-module **/

import { Component, useExternalListener, useRef, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { cva } from "@odx_owl/core/utils/variants";

export const toastVariants = cva("odx-toast", {
    variants: {
        variant: {
            default: "odx-toast--default",
            destructive: "odx-toast--destructive",
        },
    },
    defaultVariants: {
        variant: "default",
    },
});

export class Toast extends Component {
    static template = "odx_owl.Toast";
    static props = {
        className: { type: String, optional: true },
        onFocusin: { type: Function, optional: true },
        onFocusout: { type: Function, optional: true },
        onMouseenter: { type: Function, optional: true },
        onMouseleave: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        role: { type: String, optional: true },
        onSwipeDismiss: { type: Function, optional: true },
        onSwipePause: { type: Function, optional: true },
        onSwipeResume: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        variant: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        open: true,
        tag: "section",
        variant: "default",
    };

    setup() {
        this.rootRef = useRef("rootRef");
        this.state = useState({
            offsetX: 0,
            pointerId: null,
            startX: 0,
            startY: 0,
            swipe: null,
        });

        useExternalListener(window, "pointermove", (ev) => this.onPointerMove(ev));
        useExternalListener(window, "pointerup", (ev) => this.onPointerEnd(ev));
        useExternalListener(window, "pointercancel", (ev) => this.onPointerEnd(ev));
    }

    get classes() {
        return toastVariants({
            variant: this.props.variant,
            className: cn(this.props.className, {
                "odx-toast--closed": this.props.open === false && this.state.swipe !== "end",
            }),
        });
    }

    get role() {
        return this.props.role || (this.props.variant === "destructive" ? "alert" : "status");
    }

    get swipeState() {
        return this.state.swipe || undefined;
    }

    get style() {
        if (this.state.offsetX > 0 || this.state.swipe === "cancel") {
            return `transform: translateX(${this.state.offsetX}px);`;
        }
        return undefined;
    }

    onMouseenter(ev) {
        this.props.onMouseenter?.(ev);
    }

    onMouseleave(ev) {
        this.props.onMouseleave?.(ev);
    }

    onFocusin(ev) {
        this.props.onFocusin?.(ev);
    }

    onFocusout(ev) {
        this.props.onFocusout?.(ev);
    }

    canSwipeFromTarget(target) {
        if (!(target instanceof Element)) {
            return true;
        }
        return !target.closest(
            "button, a, input, select, textarea, [contenteditable='true'], .odx-toast__action, .odx-toast__close"
        );
    }

    clearSwipe() {
        this.state.pointerId = null;
        this.state.startX = 0;
        this.state.startY = 0;
    }

    resetSwipe(resume = true) {
        this.clearSwipe();
        if (this.state.swipe === "move" || this.state.offsetX > 0) {
            this.state.swipe = "cancel";
            this.state.offsetX = 0;
            if (resume) {
                this.props.onSwipeResume?.();
            }
            setTimeout(() => {
                if (this.state.swipe === "cancel" && this.state.offsetX === 0) {
                    this.state.swipe = null;
                }
            }, 180);
            return;
        }
        if (resume) {
            this.props.onSwipeResume?.();
        }
    }

    onPointerDown(ev) {
        if (this.props.open === false || ev.button > 0 || !this.canSwipeFromTarget(ev.target)) {
            return;
        }
        this.state.pointerId = ev.pointerId;
        this.state.startX = ev.clientX;
        this.state.startY = ev.clientY;
        this.state.offsetX = 0;
        this.state.swipe = null;
        this.props.onSwipePause?.();
    }

    onPointerMove(ev) {
        if (this.state.pointerId !== ev.pointerId) {
            return;
        }
        const deltaX = ev.clientX - this.state.startX;
        const deltaY = ev.clientY - this.state.startY;
        if (Math.abs(deltaY) > Math.abs(deltaX) && Math.abs(deltaY) > 8) {
            this.resetSwipe();
            return;
        }
        const offsetX = Math.max(0, deltaX);
        if (!offsetX) {
            return;
        }
        ev.preventDefault();
        this.state.swipe = "move";
        this.state.offsetX = offsetX;
    }

    onPointerEnd(ev) {
        if (this.state.pointerId !== ev.pointerId) {
            return;
        }
        const width = this.rootRef.el?.offsetWidth || 0;
        const threshold = Math.max(80, Math.min(140, width * 0.35 || 80));
        if (this.state.offsetX >= threshold) {
            this.clearSwipe();
            this.state.swipe = "end";
            this.props.onSwipeDismiss?.();
            return;
        }
        this.resetSwipe();
    }
}

export class ToastTitle extends Component {
    static template = "odx_owl.ToastTitle";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "h4",
        text: "",
    };

    get classes() {
        return cn("odx-toast__title", this.props.className);
    }
}

export class ToastDescription extends Component {
    static template = "odx_owl.ToastDescription";
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
        return cn("odx-toast__description", this.props.className);
    }
}

export class ToastAction extends Component {
    static template = "odx_owl.ToastAction";
    static props = {
        altText: { type: String, optional: true },
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
        text: "",
        type: "button",
    };

    get classes() {
        return cn("odx-toast__action", this.props.className);
    }

    get ariaLabel() {
        return this.props.ariaLabel || this.props.altText;
    }

    onClick(ev) {
        if (this.props.disabled) {
            ev.preventDefault();
            ev.stopPropagation();
            return;
        }
        this.props.onClick?.(ev);
    }
}

export class ToastClose extends Component {
    static template = "odx_owl.ToastClose";
    static props = {
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        onClick: { type: Function, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        ariaLabel: "Dismiss notification",
        className: "",
        type: "button",
    };

    get classes() {
        return cn("odx-toast__close", this.props.className);
    }

    onClick(ev) {
        this.props.onClick?.(ev);
    }
}

export class ToastViewport extends Component {
    static template = "odx_owl.ToastViewport";
    static components = {
        Toast,
        ToastAction,
        ToastClose,
        ToastDescription,
        ToastTitle,
    };
    static props = {
        state: { type: Object },
    };

    closeToast(id) {
        this.env.services.odx_toast.dismiss(id);
    }

    pauseToast(id) {
        this.env.services.odx_toast.pause?.(id);
    }

    resumeToast(id) {
        this.env.services.odx_toast.resume?.(id);
    }

    runAction(toast) {
        toast.action?.();
        this.closeToast(toast.id);
    }
}

export class Toaster extends ToastViewport {}

Toaster.template = ToastViewport.template;
Toaster.components = ToastViewport.components;
Toaster.props = ToastViewport.props;
