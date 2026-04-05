/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { Calendar } from "@odx_owl/components/calendar/calendar";
import { Popover } from "@odx_owl/components/popover/popover";
import { cn } from "@odx_owl/core/utils/cn";
import { formatDateValue, normalizeDateValue, toISODate } from "@odx_owl/core/utils/dates";
import { resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";

export class DatePicker extends Component {
    static template = "odx_owl.DatePicker";
    static components = {
        Calendar,
        Popover,
    };
    static props = {
        attrs: { type: Object, optional: true },
        ariaLabel: { type: String, optional: true },
        className: { type: String, optional: true },
        contentClassName: { type: String, optional: true },
        defaultOpen: { type: Boolean, optional: true },
        defaultValue: { optional: true, validate: () => true },
        disabled: { type: Boolean, optional: true },
        disabledDates: { optional: true, validate: () => true },
        dir: { type: String, optional: true },
        formatOptions: { type: Object, optional: true },
        locale: { type: String, optional: true },
        maxDate: { optional: true, validate: () => true },
        minDate: { optional: true, validate: () => true },
        name: { type: String, optional: true },
        onOpenChange: { type: Function, optional: true },
        onValueChange: { type: Function, optional: true },
        open: { type: Boolean, optional: true },
        placeholder: { type: String, optional: true },
        showOutsideDays: { type: Boolean, optional: true },
        value: { optional: true, validate: () => true },
        weekStartsOn: { type: Number, optional: true },
    };
    static defaultProps = {
        attrs: {},
        className: "",
        contentClassName: "",
        defaultOpen: false,
        disabled: false,
        formatOptions: { dateStyle: "medium" },
        placeholder: "Pick a date",
        showOutsideDays: true,
    };

    setup() {
        this.state = useState({
            calendarId: nextId("odx-date-picker-calendar"),
            open: this.props.open ?? this.props.defaultOpen,
            value: normalizeDateValue(this.props.value ?? this.props.defaultValue),
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
            if (nextProps.value !== undefined) {
                this.state.value = normalizeDateValue(nextProps.value);
            }
        });
    }

    get currentValue() {
        return normalizeDateValue(this.props.value ?? this.state.value);
    }

    get formattedValue() {
        return formatDateValue(this.currentValue, this.props.formatOptions, this.props.locale);
    }

    get currentIsoValue() {
        return toISODate(this.currentValue);
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get panelClasses() {
        return cn("odx-date-picker__panel", this.props.contentClassName);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get triggerClasses() {
        return cn(
            "odx-date-picker__trigger",
            {
                "odx-date-picker__trigger--placeholder": !this.currentValue,
            },
            this.props.className
        );
    }

    onCalendarValueChange(value) {
        const normalized = normalizeDateValue(value);
        if (this.props.value === undefined) {
            this.state.value = normalized;
        }
        this.props.onValueChange?.(normalized, toISODate(normalized));
        this.setOpen(false);
    }

    onTriggerKeydown(ev) {
        if (this.props.disabled) {
            return;
        }
        if (["ArrowDown", "Enter", " "].includes(ev.key)) {
            ev.preventDefault();
            this.setOpen(true);
        }
    }

    setOpen(open) {
        if (this.props.open === undefined) {
            this.state.open = open;
        }
        this.props.onOpenChange?.(open);
    }
}
