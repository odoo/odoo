/** @odoo-module **/

import { Component, useChildSubEnv, useState } from "@odoo/owl";
import { cn } from "@odx_owl/core/utils/cn";
import { isRtlDirection, resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId, sanitizeIdFragment } from "@odx_owl/core/utils/ids";

function normalizeValues(value, type) {
    if (value === undefined || value === null || value === "") {
        return [];
    }
    if (Array.isArray(value)) {
        return value;
    }
    return type === "multiple" ? [value] : [value];
}

function focusTrigger(triggers, index) {
    const target = triggers[index];
    if (target) {
        target.focus();
    }
}

export class Accordion extends Component {
    static template = "odx_owl.Accordion";
    static props = {
        className: { type: String, optional: true },
        collapsible: { type: Boolean, optional: true },
        defaultValue: { optional: true, validate: () => true },
        dir: { type: String, optional: true },
        loop: { type: Boolean, optional: true },
        onValueChange: { type: Function, optional: true },
        orientation: { type: String, optional: true },
        slots: { type: Object, optional: true },
        type: { type: String, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        className: "",
        collapsible: true,
        loop: true,
        orientation: "vertical",
        type: "single",
    };

    setup() {
        const self = this;
        this.state = useState({
            baseId: nextId("odx-accordion"),
            values: normalizeValues(this.props.value ?? this.props.defaultValue, this.props.type),
        });

        useChildSubEnv({
            odxAccordion: {
                getValue: () => self.currentValues,
                isOpen: (value) => self.currentValues.includes(value),
                toggle: (value) => self.toggle(value),
                get loop() {
                    return self.props.loop;
                },
                get orientation() {
                    return self.props.orientation;
                },
                get dir() {
                    return self.direction;
                },
                getTriggerId: (value) =>
                    `${self.state.baseId}-trigger-${sanitizeIdFragment(value)}`,
                getContentId: (value) =>
                    `${self.state.baseId}-content-${sanitizeIdFragment(value)}`,
            },
        });
    }

    get currentValues() {
        return normalizeValues(this.props.value ?? this.state.values, this.props.type);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get classes() {
        return cn("odx-accordion", this.props.className);
    }

    toggle(value) {
        const current = this.currentValues;
        const isOpen = current.includes(value);
        let nextValues;
        if (this.props.type === "multiple") {
            nextValues = isOpen ? current.filter((item) => item !== value) : [...current, value];
        } else if (isOpen) {
            nextValues = this.props.collapsible ? [] : [value];
        } else {
            nextValues = [value];
        }
        if (this.props.value === undefined) {
            this.state.values = nextValues;
        }
        this.props.onValueChange?.(this.props.type === "multiple" ? nextValues : nextValues[0] || null);
    }
}

export class AccordionItem extends Component {
    static template = "odx_owl.AccordionItem";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { validate: () => true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
    };

    setup() {
        const self = this;
        useChildSubEnv({
            odxAccordionItem: {
                get disabled() {
                    return self.props.disabled;
                },
                get value() {
                    return self.props.value;
                },
            },
        });
    }

    get isOpen() {
        return this.env.odxAccordion.isOpen(this.props.value);
    }

    get classes() {
        return cn(
            "odx-accordion__item",
            {
                "odx-accordion__item--disabled": this.props.disabled,
                "odx-accordion__item--open": this.isOpen,
            },
            this.props.className
        );
    }
}

export class AccordionHeader extends Component {
    static template = "odx_owl.AccordionHeader";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
    };
    static defaultProps = {
        className: "",
    };

    get isOpen() {
        return this.env.odxAccordion.isOpen(this.value);
    }

    get isDisabled() {
        return Boolean(this.env.odxAccordionItem?.disabled);
    }

    get value() {
        return this.env.odxAccordionItem?.value;
    }

    get classes() {
        return cn("odx-accordion__header", this.props.className);
    }
}

export class AccordionTrigger extends Component {
    static template = "odx_owl.AccordionTrigger";
    static props = {
        className: { type: String, optional: true },
        disabled: { type: Boolean, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        className: "",
        disabled: false,
    };

    get value() {
        return this.props.value ?? this.env.odxAccordionItem?.value;
    }

    get isOpen() {
        return this.env.odxAccordion.isOpen(this.value);
    }

    get isDisabled() {
        return Boolean(this.props.disabled || this.env.odxAccordionItem?.disabled);
    }

    get triggerId() {
        return this.env.odxAccordion.getTriggerId(this.value);
    }

    get contentId() {
        return this.env.odxAccordion.getContentId(this.value);
    }

    get classes() {
        return cn(
            "odx-accordion__trigger",
            { "odx-accordion__trigger--disabled": this.isDisabled },
            this.props.className
        );
    }

    toggle() {
        if (!this.isDisabled) {
            this.env.odxAccordion.toggle(this.value);
        }
    }

    onKeydown(ev) {
        const orientation = this.env.odxAccordion.orientation || "vertical";
        const isVertical = orientation !== "horizontal";
        const supportedKeys = isVertical
            ? ["ArrowDown", "ArrowUp", "Home", "End"]
            : ["ArrowRight", "ArrowLeft", "Home", "End"];
        if (!supportedKeys.includes(ev.key)) {
            return;
        }
        const root = ev.currentTarget.closest(".odx-accordion");
        if (!root) {
            return;
        }
        const triggers = [...root.querySelectorAll(".odx-accordion__trigger:not([disabled])")];
        const currentIndex = triggers.indexOf(ev.currentTarget);
        if (!triggers.length || currentIndex === -1) {
            return;
        }
        ev.preventDefault();
        if (ev.key === "Home") {
            focusTrigger(triggers, 0);
            return;
        }
        if (ev.key === "End") {
            focusTrigger(triggers, triggers.length - 1);
            return;
        }
        const isRtl = !isVertical && isRtlDirection(this.env.odxAccordion.dir);
        const direction =
            ev.key === "ArrowDown"
                ? 1
                : ev.key === "ArrowUp"
                  ? -1
                  : ev.key === "ArrowRight"
                    ? isRtl ? -1 : 1
                    : isRtl ? 1 : -1;
        const nextIndex = currentIndex + direction;
        if (nextIndex < 0 || nextIndex >= triggers.length) {
            if (!this.env.odxAccordion.loop) {
                return;
            }
            focusTrigger(triggers, (nextIndex + triggers.length) % triggers.length);
            return;
        }
        focusTrigger(triggers, nextIndex);
    }
}

export class AccordionContent extends Component {
    static template = "odx_owl.AccordionContent";
    static props = {
        className: { type: String, optional: true },
        slots: { type: Object, optional: true },
        value: { optional: true, validate: () => true },
    };
    static defaultProps = {
        className: "",
    };

    get value() {
        return this.props.value ?? this.env.odxAccordionItem?.value;
    }

    get isOpen() {
        return this.env.odxAccordion.isOpen(this.value);
    }

    get triggerId() {
        return this.env.odxAccordion.getTriggerId(this.value);
    }

    get contentId() {
        return this.env.odxAccordion.getContentId(this.value);
    }

    get classes() {
        return cn(
            "odx-accordion__content",
            { "odx-accordion__content--open": this.isOpen },
            this.props.className
        );
    }
}
