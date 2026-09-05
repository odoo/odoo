import { _t } from "@web/core/l10n/translation";
import { is24HourFormat } from "@web/core/l10n/time";
import { parseXML } from "@web/core/utils/xml";
import { getColor, getFormattedDateSpan } from "@web/views/calendar/utils";
import { CARD_ATTRIBUTE } from "@web/views/card/card_arch_parser";
import { CardPopover } from "@web/views/card/card_popover/card_popover";

import { Component, t, useListener, useProps } from "@odoo/owl";

export class CalendarCommonPopover extends Component {
    static template = "web.CalendarCommonPopover";
    static components = { CardPopover };
    static defaultFooterButtonsTemplate = "web.CalendarCommonPopover.DefaultFooterButtons";

    props = useProps({
        close: t.function(),
        model: t.object(),
        record: t.object(),
        openRecord: t.function().optional(() => () => {}),
        deleteRecord: t.function().optional(() => () => {}),
    });

    setup() {
        this.time = null;
        this.timeDuration = null;
        this.date = null;
        this.dateDuration = null;

        useListener(
            window,
            "pointerdown",
            (e) => {
                if (!e.target.closest(`.fc-event[data-event-id="${this.props.record.id}"]`)) {
                    e.preventDefault();
                }
            },
            { capture: true }
        );

        this.computeDateTimeAndDuration();
    }

    get resId() {
        return this.props.record.id;
    }

    get readonly() {
        return !this.props.model.canEdit;
    }

    get cardPopoverProps() {
        const { meta } = this.props.model;
        const color = getColor(this.props.record.colorIndex);
        return {
            close: this.props.close,
            fields: meta.fields,
            resModel: this.props.model.resModel,
            resId: this.resId,
            popoverNode: meta.popoverNode,
            readonly: this.readonly,
            rootClass: `o_cw_popover o_calendar_color_${typeof color === "number" ? color : 0}`,
            context: meta.context,
            reloadOnClose: () => this.props.model.load(),
            openRecord: this.props.openRecord,
            getDefaultPopoverBody: () => this.getDefaultPopoverBody(),
        };
    }

    get title() {
        return this.props.record.title || "";
    }

    get isEventEditable() {
        return !this.readonly;
    }

    get isEventDeletable() {
        return this.props.model.canDelete;
    }

    get isEventViewable() {
        return true;
    }

    computeDateTimeAndDuration() {
        const record = this.props.record;
        if (!record) {
            return;
        }
        const { start, end } = record;
        const isSameDay = start.hasSame(end, "day");

        if (!record.isTimeHidden && !record.isAllDay && isSameDay) {
            this.time = this.formatTimeRange(start, end, is24HourFormat() ? "HH:mm" : "hh:mm a");
            this.timeDuration = this.formatTimeDuration(end.diff(start, ["hours", "minutes"]));
        }
        if (!this.props.model.isDateHidden) {
            this.date = this.formatDateRange(start, end);
            this.dateDuration = this.formatDateDuration(start, end);
        }
    }

    formatTimeRange(start, end, timeFormat) {
        return `${start.toFormat(timeFormat)} - ${end.toFormat(timeFormat)}`;
    }

    formatTimeDuration(duration) {
        const formatParts = [];
        if (duration.hours > 0) {
            const hourString = duration.hours === 1 ? _t("hour") : _t("hours");
            formatParts.push(`h '${hourString}'`);
        }
        if (duration.minutes > 0) {
            const minuteStr = duration.minutes === 1 ? _t("minute") : _t("minutes");
            formatParts.push(`m '${minuteStr}'`);
        }
        return duration.toFormat(formatParts.join(", "));
    }

    formatDateRange(start, end) {
        return getFormattedDateSpan(start, end);
    }

    formatDateDuration(start, end) {
        if (!this.props.record.isAllDay || start.hasSame(end, "day")) {
            return null;
        }
        return end
            .plus({ day: 1 })
            .diff(start, "days")
            .toFormat(`d '${_t("days")}'`);
    }

    getDefaultPopoverBody() {
        const items = [];
        if (this.date) {
            const duration = this.dateDuration
                ? ` <small class="fw-bold">${this.dateDuration}</small>`
                : "";
            items.push(`
                <div class="d-flex align-items-center gap-2">
                    <i class="oi oi-fw oi-filled text-400" data-icon="calendar_today"/>
                    <span class="fw-bold">${this.date}</span>${duration}
                </div>
            `);
        }
        if (this.time) {
            const duration = this.timeDuration
                ? ` <small class="fw-bold">(${this.timeDuration})</small>`
                : "";
            items.push(`
                <div class="d-flex align-items-center gap-2">
                    <i class="oi oi-fw text-400" data-icon="schedule"/>
                    <span class="fw-bold">${this.time}</span>${duration}
                </div>
            `);
        }
        // Retro-compatibility layer: generate a card template from the fields in the arch
        for (const fieldNode of Object.values(this.props.model.meta.popoverFieldNodes)) {
            if (["1", "True"].includes(fieldNode.invisible)) {
                items.push(`<field name="${fieldNode.name}" invisible="1"/>`);
                continue;
            }
            const widget = `widget="${fieldNode.widget || fieldNode.type}"`;
            const options = `options='${JSON.stringify(fieldNode.options)}'`;
            const readonly = fieldNode.readonly ? `readonly="${fieldNode.readonly}"` : "";
            const field = `<field name="${fieldNode.name}" ${options} ${widget} ${readonly}/>`;
            let label = "";
            if (!fieldNode.options.noLabel && fieldNode.type !== "properties") {
                label = fieldNode.options.icon
                    ? `<i class="oi oi-fw text-400" title="${fieldNode.string}" data-icon="${fieldNode.options.icon}"/>`
                    : `<span class="fw-bold">${fieldNode.string}</span>`;
            }
            const invisible = fieldNode.invisible ? `invisible="${fieldNode.invisible}"` : "";
            items.push(
                `<div class="d-flex align-items-center gap-2" ${invisible}>${label}${field}</div>`
            );
        }
        return parseXML(`<t t-name="${CARD_ATTRIBUTE}" class="gap-3">${items.join("")}</t>`);
    }

    onEditEvent() {
        this.props.openRecord();
        this.props.close();
    }

    onDeleteEvent() {
        this.props.deleteRecord();
        this.props.close();
    }
}
