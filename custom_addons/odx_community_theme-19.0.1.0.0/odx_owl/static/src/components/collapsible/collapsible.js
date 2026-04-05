/** @odoo-module **/

import { Component, onWillUpdateProps, useChildSubEnv, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { nextId } from "@odx_owl/core/utils/ids";

export class Collapsible extends Component {
    static template = "odx_owl.Collapsible";
    static props = {
        className: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        disabled: { type: Boolean, optional: true },
        onOpenChange: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        defaultOpen: false,
        disabled: false,
        tag: "div",
    };

    setup() {
        const self = this;
        this.state = useState({
            baseId: nextId("odx-collapsible"),
            open: this.props.open ?? this.props.defaultOpen,
        });

        useChildSubEnv({
            odxCollapsible: {
                get contentId() {
                    return `${self.state.baseId}-content`;
                },
                get disabled() {
                    return self.props.disabled;
                },
                get isOpen() {
                    return self.isOpen;
                },
                get triggerId() {
                    return `${self.state.baseId}-trigger`;
                },
                setOpen: (open) => self.setOpen(open),
                toggle: () => self.toggle(),
            },
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
        });
    }

    get classes() {
        return cn("odx-collapsible", this.props.className);
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    setOpen(open) {
        if (this.props.disabled) {
            return;
        }
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        this.props.onOpenChange?.(open);
    }

    toggle() {
        this.setOpen(!this.isOpen);
    }
}

export class CollapsibleTrigger extends Component {
    static template = "odx_owl.CollapsibleTrigger";
    static props = {
        ariaLabel: { type: String, optional: true },
        attrs: { type: Object, optional: true },
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        label: { type: String, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
        type: { type: String, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        disabled: false,
        label: "",
        tag: "button",
        type: "button",
    };

    get classes() {
        return cn(
            "odx-collapsible__trigger",
            {
                "odx-collapsible__trigger--open": this.isOpen,
            },
            this.props.className
        );
    }

    get isDisabled() {
        return this.props.disabled || this.env.odxCollapsible.disabled;
    }

    get isOpen() {
        return this.env.odxCollapsible.isOpen;
    }

    toggle(ev) {
        if (this.isDisabled) {
            ev.preventDefault();
            return;
        }
        this.env.odxCollapsible.toggle();
    }
}

export class CollapsibleContent extends Component {
    static template = "odx_owl.CollapsibleContent";
    static props = {
        className: { type: String, optional: true },
        forceMount: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        tag: { type: String, optional: true },
    };
    static defaultProps = {
        className: "",
        forceMount: false,
        tag: "div",
    };

    get classes() {
        return cn(
            "odx-collapsible__content",
            {
                "odx-collapsible__content--open": this.isOpen,
            },
            this.props.className
        );
    }

    get isOpen() {
        return this.env.odxCollapsible.isOpen;
    }

    get shouldRender() {
        return this.props.forceMount || this.isOpen;
    }
}
