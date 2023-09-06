/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { Dialog } from "@web/core/dialog/dialog";
import { evaluateBooleanExpr } from "@web/core/py_js/py";
import { is24HourFormat } from "@web/core/l10n/dates";
import { Field } from "@web/views/fields/field";
import { Record } from "@web/views/record";
import { getFormattedDateSpan } from "@web/views/calendar/utils";

import { Component } from "@odoo/owl";

export class CalendarCommonPopover extends Component {
    setup() {
        this.time = null;
        this.timeDuration = null;
        this.date = null;
        this.dateDuration = null;

        this.computeDateTimeAndDuration();
    }

    get activeFields() {
        return this.props.model.activeFields;
    }
    get isEventEditable() {
        return true;
    }
    get isEventDeletable() {
        return this.props.model.canDelete;
    }
    get hasFooter() {
        return this.isEventEditable || this.isEventDeletable;
    }

    isInvisible(fieldNode, record) {
        return evaluateBooleanExpr(fieldNode.invisible, record.evalContextWithVirtualIds);
    }

    computeDateTimeAndDuration() {
        const record = this.props.record;
        const { start, end } = record;
        const isSameDay = start.hasSame(end, "day");

        if (!record.isTimeHidden && !record.isAllDay && isSameDay) {
            const timeFormat = is24HourFormat() ? "HH:mm" : "hh:mm a";
            this.time = `${start.toFormat(timeFormat)} - ${end.toFormat(timeFormat)}`;

            const duration = end.diff(start, ["hours", "minutes"]);
            const formatParts = [];
            if (duration.hours > 0) {
                const hourString = duration.hours === 1 ? _t("hour") : _t("hours");
                formatParts.push(`h '${hourString}'`);
            }
            if (duration.minutes > 0) {
                const minuteStr = duration.minutes === 1 ? _t("minute") : _t("minutes");
                formatParts.push(`m '${minuteStr}'`);
            }
            this.timeDuration = duration.toFormat(formatParts.join(", "));
        }

        if (!this.props.model.isDateHidden) {
            this.date = getFormattedDateSpan(start, end);

            if (record.isAllDay) {
                if (isSameDay) {
                    this.dateDuration = _t("All day");
                } else {
                    const duration = end.plus({ day: 1 }).diff(start, "days");
                    this.dateDuration = duration.toFormat(`d '${_t("days")}'`);
                }
            }
        }
    }

    onEditEvent() {
        this.props.editRecord(this.props.record);
        this.props.close();
    }
    onDeleteEvent() {
        this.props.deleteRecord(this.props.record);
        this.props.close();
    }
}
CalendarCommonPopover.components = {
    Dialog,
    Field,
    Record,
};
CalendarCommonPopover.template = "web.CalendarCommonPopover";
CalendarCommonPopover.subTemplates = {
    popover: "web.CalendarCommonPopover.popover",
    body: "web.CalendarCommonPopover.body",
    footer: "web.CalendarCommonPopover.footer",
};
CalendarCommonPopover.props = {
    close: Function,
    record: Object,
    model: Object,
    createRecord: Function,
    deleteRecord: Function,
    editRecord: Function,
};
