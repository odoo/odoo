/** @odoo-module **/

import {
    Component,
    onMounted,
    onRendered,
    onWillDestroy,
    onWillUpdateProps,
    reactive,
    useChildSubEnv,
    useEffect,
    useRef,
    useState,
    xml,
} from "@odoo/owl";
import { usePopover } from "@web/core/popover/popover_hook";
import { cn } from "@odx_owl/core/utils/cn";
import { resolveOverlayPosition } from "@odx_owl/core/utils/overlay_position";

class OdxPopoverPanel extends Component {
    static template = xml`
        <div t-att-class="props.className">
            <t t-slot="content">
                <t t-if="props.text" t-esc="props.text"/>
            </t>
        </div>
    `;
    static props = {
        className: { type: String, optional: true },
        close: { type: Function, optional: true },
        onClosed: { type: Function, optional: true },
        onOpened: { type: Function, optional: true },
        refresher: Object,
        slots: Object,
        text: { type: String, optional: true },
    };

    setup() {
        onRendered(() => {
            this.props.refresher.token;
        });
        onMounted(() => this.props.onOpened?.());
        onWillDestroy(() => this.props.onClosed?.());
    }
}

export class PopoverTrigger extends Component {
    static template = "odx_owl.PopoverTrigger";
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
        return cn("odx-popover__trigger-content", this.props.className);
    }

    get isOpen() {
        return this.env.odxPopover?.isOpen;
    }
}

export class PopoverAnchor extends Component {
    static template = "odx_owl.PopoverAnchor";
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
        return cn("odx-popover__anchor-content", this.props.className);
    }
}

export class PopoverContent extends Component {
    static template = "odx_owl.PopoverContent";
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
        return cn("odx-popover__content", this.props.className);
    }
}

export class PopoverClose extends Component {
    static template = "odx_owl.PopoverClose";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        tag: "button",
        text: "",
    };

    get classes() {
        return cn("odx-popover__close", this.props.className);
    }

    onClick() {
        this.env.odxPopover?.close?.();
    }
}

export class Popover extends Component {
    static template = "odx_owl.Popover";
    static props = {
        align: { type: String, optional: true },
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        onOpenChange: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        position: { type: String, optional: true },
        side: { type: String, optional: true },
        slots: { type: Object, optional: true },
        text: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        contentClassName: "",
        defaultOpen: false,
        disabled: false,
        position: "bottom",
    };

    setup() {
        const self = this;
        this.anchorRef = useRef("anchorRef");
        this.triggerRef = useRef("triggerRef");
        this.state = useState({
            open: this.props.open ?? this.props.defaultOpen,
        });
        this.refresher = reactive({ token: 0 });

        useChildSubEnv({
            odxPopover: {
                close: () => self.setOpen(false),
                get isOpen() {
                    return self.isOpen;
                },
                setOpen: (open) => self.setOpen(open),
                toggle: () => self.toggle(),
            },
        });

        this.popover = usePopover(OdxPopoverPanel, {
            animation: false,
            arrow: false,
            closeOnEscape: true,
            env: this.__owl__.childEnv,
            onClose: () => this.setOpen(false),
            popoverClass: "odx-popover__surface",
            position: this.resolvedPosition,
            setActiveElement: false,
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
        });

        useEffect(
            (open, target) => {
                if (!target) {
                    return;
                }
                if (open && !this.props.disabled) {
                    this.openPanel(target);
                } else {
                    this.popover.close();
                }
                return () => this.popover.close();
            },
            () => [this.isOpen, this.targetEl]
        );

        onRendered(() => {
            if (this.popover.isOpen) {
                this.refresher.token++;
            }
        });
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get triggerClasses() {
        return cn("odx-popover__trigger", this.props.className);
    }

    get hasAnchor() {
        return Boolean(this.props.slots?.anchor);
    }

    get resolvedPosition() {
        return resolveOverlayPosition({
            align: this.props.align,
            fallback: "bottom",
            position: this.props.position,
            side: this.props.side,
        });
    }

    get targetEl() {
        return this.anchorRef.el || this.triggerRef.el;
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        this.props.onOpenChange?.(open);
    }

    toggle() {
        if (!this.props.disabled) {
            this.setOpen(!this.isOpen);
        }
    }

    onTriggerClick(ev) {
        ev.preventDefault();
        ev.stopPropagation();
        this.toggle();
    }

    openPanel(target) {
        if (!target?.isConnected) {
            return;
        }
        this.popover.open(target, {
            className: cn("odx-popover__panel", this.props.contentClassName),
            onOpened: () => this.props.onOpenChange?.(true),
            refresher: this.refresher,
            slots: this.props.slots,
            text: this.props.text,
        });
    }
}
