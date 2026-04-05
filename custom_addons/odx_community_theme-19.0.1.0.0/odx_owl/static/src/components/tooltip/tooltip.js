/** @odoo-module **/

import {
    Component,
    onWillDestroy,
    reactive,
    useChildSubEnv,
    useRef,
    xml,
} from "@odoo/owl";
import { browser } from "@web/core/browser/browser";
import { usePopover } from "@web/core/popover/popover_hook";
import { cn } from "@odx_owl/core/utils/cn";
import { nextId } from "@odx_owl/core/utils/ids";
import { resolveOverlayPosition } from "@odx_owl/core/utils/overlay_position";

class OdxTooltipPanel extends Component {
    static template = xml`
        <div
            t-att-id="props.id"
            t-att-class="props.className"
            role="tooltip"
            t-att-data-state="props.open ? 'open' : 'closed'"
            t-on-mouseenter="props.onEnter"
            t-on-mouseleave="props.onLeave"
        >
            <t t-slot="content">
                <t t-esc="props.text"/>
            </t>
        </div>
    `;
    static props = {
        className: { type: String, optional: true },
        id: { type: String, optional: true },
        onEnter: { type: Function, optional: true },
        onLeave: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        slots: Object,
        text: { type: String, optional: true },
    };
}

export class TooltipProvider extends Component {
    static template = "odx_owl.TooltipProvider";
    static props = {
        delayDuration: { type: Number, optional: true },
        disableHoverableContent: { type: Boolean, optional: true },
        skipDelayDuration: { type: Number, optional: true },
        slots: Object,
    };
    static defaultProps = {
        delayDuration: 200,
        disableHoverableContent: false,
        skipDelayDuration: 300,
    };

    setup() {
        const self = this;
        this.state = reactive({
            skipUntil: 0,
        });
        useChildSubEnv({
            odxTooltipProvider: {
                get delayDuration() {
                    return self.props.delayDuration;
                },
                get disableHoverableContent() {
                    return self.props.disableHoverableContent;
                },
                markRecentlyOpen() {
                    self.state.skipUntil = Date.now() + Math.max(0, self.props.skipDelayDuration);
                },
                shouldSkipDelay() {
                    return Date.now() < self.state.skipUntil;
                },
            },
        });
    }
}

export class TooltipTrigger extends Component {
    static template = "odx_owl.TooltipTrigger";
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
        return cn("odx-tooltip__trigger-content", this.props.className);
    }

    get tooltipId() {
        return this.env.odxTooltip?.id;
    }
}

export class TooltipContent extends Component {
    static template = "odx_owl.TooltipContent";
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

    get classes() {
        return cn("odx-tooltip__content", this.props.className);
    }
}

export class Tooltip extends Component {
    static template = "odx_owl.Tooltip";
    static props = {
        align: { type: String, optional: true },
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        delay: { type: Number, optional: true },
        delayDuration: { type: Number, optional: true },
        disableHoverableContent: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        contentClassName: "",
        disabled: false,
        position: "top",
        text: "",
    };

    setup() {
        const self = this;
        this.triggerRef = useRef("triggerRef");
        this.state = reactive({
            closeTimer: null,
            id: nextId("odx-tooltip"),
            open: false,
            timer: null,
        });
        useChildSubEnv({
            odxTooltip: {
                get id() {
                    return self.state.id;
                },
                get isOpen() {
                    return self.state.open;
                },
            },
        });
        this.popover = usePopover(OdxTooltipPanel, {
            animation: false,
            arrow: false,
            closeOnClickAway: true,
            closeOnEscape: true,
            onClose: () => {
                this.state.open = false;
            },
            popoverClass: "odx-tooltip__surface",
            position: this.resolvedPosition,
            setActiveElement: false,
        });

        onWillDestroy(() => {
            this.clearTimer();
            this.clearCloseTimer();
        });
    }

    get triggerClasses() {
        return cn("odx-tooltip__trigger", this.props.className);
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: "top",
            position: this.props.position,
            side: this.props.side,
        });
    }

    get tooltipProvider() {
        return this.env.odxTooltipProvider;
    }

    clearTimer() {
        if (this.state.timer) {
            browser.clearTimeout(this.state.timer);
            this.state.timer = null;
        }
    }

    clearCloseTimer() {
        if (this.state.closeTimer) {
            browser.clearTimeout(this.state.closeTimer);
            this.state.closeTimer = null;
        }
    }

    get openDelay() {
        if (this.tooltipProvider?.shouldSkipDelay?.()) {
            return 0;
        }
        return this.props.delayDuration ?? this.props.delay ?? this.tooltipProvider?.delayDuration ?? 200;
    }

    get hoverableContentDisabled() {
        return this.props.disableHoverableContent ?? this.tooltipProvider?.disableHoverableContent ?? false;
    }

    markRecentlyOpen() {
        this.tooltipProvider?.markRecentlyOpen?.();
    }

    keepOpen() {
        this.clearTimer();
        this.clearCloseTimer();
    }

    open() {
        if (this.props.disabled || !this.triggerRef.el?.isConnected) {
            return;
        }
        this.keepOpen();
        this.state.open = true;
        this.popover.open(this.triggerRef.el, {
            className: cn("odx-tooltip__panel", this.props.contentClassName),
            id: this.state.id,
            onEnter: () => this.onPanelEnter(),
            onLeave: () => this.onPanelLeave(),
            open: true,
            slots: this.props.slots,
            text: this.props.text,
        });
    }

    openImmediate() {
        this.keepOpen();
        this.open();
    }

    scheduleOpen() {
        this.keepOpen();
        if (!this.openDelay) {
            this.open();
            return;
        }
        this.state.timer = browser.setTimeout(() => {
            this.open();
            this.state.timer = null;
        }, this.openDelay);
    }

    onTriggerLeave() {
        if (this.state.open) {
            this.markRecentlyOpen();
        }
        if (this.hoverableContentDisabled) {
            this.close();
            return;
        }
        this.scheduleClose();
    }

    scheduleClose() {
        this.clearTimer();
        this.clearCloseTimer();
        this.state.closeTimer = browser.setTimeout(() => {
            this.state.closeTimer = null;
            this.close();
        }, 40);
    }

    onPanelEnter() {
        if (!this.hoverableContentDisabled) {
            this.keepOpen();
        }
    }

    onPanelLeave() {
        if (!this.hoverableContentDisabled) {
            this.markRecentlyOpen();
            this.scheduleClose();
        }
    }

    close() {
        this.keepOpen();
        this.state.open = false;
        this.popover.close();
    }
}
