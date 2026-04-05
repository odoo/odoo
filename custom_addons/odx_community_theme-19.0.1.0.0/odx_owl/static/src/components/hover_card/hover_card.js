/** @odoo-module **/

import { Component, onWillDestroy, reactive, useChildSubEnv, useRef, xml } from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { usePopover } from "@web/core/popover/popover_hook";
import { cn } from "@odx_owl/core/utils/cn";
import { resolveOverlayPosition } from "@odx_owl/core/utils/overlay_position";

class OdxHoverCardPanel extends Component {
    static template = xml`
        <div
            t-att-class="props.className"
            t-on-mouseenter="props.onEnter"
            t-on-mouseleave="props.onLeave"
            t-on-focusin="props.onEnter"
            t-on-focusout="props.onLeave"
        >
            <t t-slot="content"/>
        </div>
    `;
    static props = {
        className: { type: String, optional: true },
        onEnter: { type: Function, optional: true },
        onLeave: { type: Function, optional: true },
        slots: Object,
    };
}

export class HoverCardTrigger extends Component {
    static template = "odx_owl.HoverCardTrigger";
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
        return cn("odx-hover-card__trigger-content", this.props.className);
    }

    get isOpen() {
        return this.env.odxHoverCard?.isOpen;
    }
}

export class HoverCardContent extends Component {
    static template = "odx_owl.HoverCardContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "div",
    };

    get classes() {
        return cn("odx-hover-card__content", this.props.className);
    }
}

export class HoverCard extends Component {
    static template = "odx_owl.HoverCard";
    static props = {
        align: { type: String, optional: true },
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        closeDelay: { type: Number, optional: true },
        openDelay: { type: Number, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
        contentClassName: "",
        closeDelay: 100,
        disabled: false,
        openDelay: 250,
        position: "bottom",
    };

    setup() {
        const self = this;
        this.triggerRef = useRef("triggerRef");
        this.state = reactive({
            closeTimer: null,
            open: false,
            openTimer: null,
        });
        useChildSubEnv({
            odxHoverCard: {
                get isOpen() {
                    return self.state.open;
                },
            },
        });
        this.popover = usePopover(OdxHoverCardPanel, {
            animation: false,
            arrow: false,
            closeOnClickAway: true,
            closeOnEscape: true,
            onClose: () => {
                this.state.open = false;
            },
            popoverClass: "odx-hover-card__surface",
            position: this.resolvedPosition,
            setActiveElement: false,
        });

        onWillDestroy(() => {
            this.clearOpenTimer();
            this.clearCloseTimer();
            this.popover.close();
        });
    }

    get triggerClasses() {
        return cn("odx-hover-card__trigger", this.props.className);
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: "bottom",
            position: this.props.position,
            side: this.props.side,
        });
    }

    clearOpenTimer() {
        if (this.state.openTimer) {
            browser.clearTimeout(this.state.openTimer);
            this.state.openTimer = null;
        }
    }

    clearCloseTimer() {
        if (this.state.closeTimer) {
            browser.clearTimeout(this.state.closeTimer);
            this.state.closeTimer = null;
        }
    }

    open() {
        if (this.props.disabled || !this.triggerRef.el?.isConnected) {
            return;
        }
        this.state.open = true;
        this.popover.open(this.triggerRef.el, {
            className: cn("odx-hover-card__panel", this.props.contentClassName),
            onEnter: () => this.keepOpen(),
            onLeave: () => this.scheduleClose(),
            slots: this.props.slots,
        });
    }

    keepOpen() {
        this.clearOpenTimer();
        this.clearCloseTimer();
    }

    scheduleOpen() {
        this.keepOpen();
        this.state.openTimer = browser.setTimeout(() => {
            this.open();
            this.state.openTimer = null;
        }, this.props.openDelay);
    }

    scheduleClose() {
        this.clearOpenTimer();
        this.clearCloseTimer();
        this.state.closeTimer = browser.setTimeout(() => {
            this.state.open = false;
            this.popover.close();
            this.state.closeTimer = null;
        }, this.props.closeDelay);
    }
}
