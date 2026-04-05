/** @odoo-module **/

import { Component, onWillUpdateProps, useState } from "@odoo/owl";
import { Calendar } from "@odx_owl/components/calendar/calendar";
import { Popover } from "@odx_owl/components/popover/popover";
import { cn } from "@odx_owl/core/utils/cn";
import { formatDateRangeValue, normalizeDateRange, toISODateRange } from "@odx_owl/core/utils/dates";
import { resolveDirection } from "@odx_owl/core/utils/direction";
import { nextId } from "@odx_owl/core/utils/ids";

export class DateRangePicker extends Component {
    static template = "odx_owl.DateRangePicker";
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
        numberOfMonths: { type: Number, optional: true },
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
        formatOptions: { month: "short", day: "2-digit", year: "numeric" },
        numberOfMonths: 2,
        placeholder: "Pick a date range",
        showOutsideDays: true,
    };

    setup() {
        this.state = useState({
            calendarId: nextId("odx-date-range-picker-calendar"),
            open: this.props.open ?? this.props.defaultOpen,
            value: normalizeDateRange(this.props.value ?? this.props.defaultValue),
        });

        onWillUpdateProps((nextProps) => {
            if (nextProps.open !== undefined) {
                this.state.open = nextProps.open;
            }
            if (nextProps.value !== undefined) {
                this.state.value = normalizeDateRange(nextProps.value);
            }
        });
    }

    get currentIsoRange() {
        return toISODateRange(this.currentValue);
    }

    get currentValue() {
        return normalizeDateRange(this.props.value ?? this.state.value);
    }

    get formattedValue() {
        return formatDateRangeValue(this.currentValue, this.props.formatOptions, this.props.locale);
    }

    get hasCompleteRange() {
        return Boolean(this.currentValue?.from && this.currentValue?.to);
    }

    get isOpen() {
        return this.props.open ?? this.state.open;
    }

    get panelClasses() {
        return cn("odx-date-picker__panel odx-date-range-picker__panel", this.props.contentClassName);
    }

    get direction() {
        return resolveDirection(this.props.dir);
    }

    get triggerClasses() {
        return cn(
            "odx-date-picker__trigger odx-date-range-picker__trigger",
            {
                "odx-date-picker__trigger--placeholder": !this.currentValue?.from,
            },
            this.props.className
        );
    }

    onCalendarValueChange(value) {
        const normalized = normalizeDateRange(value);
        if (this.props.value === undefined) {
            this.state.value = normalized;
        }
        this.props.onValueChange?.(normalized, toISODateRange(normalized));
        if (normalized?.from && normalized?.to) {
            this.setOpen(false);
        }
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
