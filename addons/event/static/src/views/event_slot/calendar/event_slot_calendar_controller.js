import { CalendarController } from "@web/views/calendar/calendar_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatFloatTime } from "@web/views/fields/formatters";
import { parseTime } from "@web/core/l10n/time";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

import { EventSlotCalendarMultiSelectionButtons } from "./event_slot_multi_selection_buttons";

const { DateTime } = luxon;

export class EventSlotCalendarController extends CalendarController {
    static template = "event.EventSlotCalendarController";
    static components = {
        ...CalendarController.components,
        MultiSelectionButtons: EventSlotCalendarMultiSelectionButtons,
    };

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
    }

    /**
     * Check if user tries to create slots outside of the event time range.
     * If so, ask for confirmation to extend the event time range and include the new slots.
     *
     * @param {Array} slotDates
     * @param {Time} slotStart
     * @param {Time} slotEnd
     * @returns {boolean} Whether or not the given slots can be created.
     */
    async checkAndConfirmSlotsCreation(slotDates, slotStart, slotEnd) {
        const { id: eventId, start: eventStartDatetime, end: eventEndDatetime, tz: eventTz } = this.model.data.event || {};
        if (!eventId || !eventStartDatetime || !eventEndDatetime || !eventTz || !slotDates?.length || !slotStart || !slotEnd) {
            return true;
        }
        // Check if slots are within the event time range.
        // NB: Event and slot datetimes can be compared as they're both in the event timezone
        // (cf model 'load' and 'normalizeRecord' methods).
        const earliestSlotStart = DateTime.min(...slotDates).plus(slotStart.toObject());
        const latestSlotEnd = DateTime.max(...slotDates).plus(slotEnd.toObject());
        if (eventStartDatetime <= earliestSlotStart && latestSlotEnd <= eventEndDatetime) {
            return true;
        }
        // Some slots are out of event time range, ask for confirmation to extend the range.
        const newEventStart = DateTime.min(earliestSlotStart, eventStartDatetime);
        const newEventEnd = DateTime.max(latestSlotEnd, eventEndDatetime);
        return await new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                title: _t("Confirmation"),
                body: _t(
                    "Adding these slots will automatically adjust the event's time range to include them.\n\n" +
                    "From:\t%(start)s - %(end)s\n" +
                    "To:\t\t%(new_start)s - %(new_end)s\n"
                , {
                    start: eventStartDatetime.toLocaleString(DateTime.DATETIME_MED),
                    end: eventEndDatetime.toLocaleString(DateTime.DATETIME_MED),
                    new_start: newEventStart.toLocaleString(DateTime.DATETIME_MED),
                    new_end: newEventEnd.toLocaleString(DateTime.DATETIME_MED),
                }),
                confirmLabel: _t("Update Event"),
                confirm: async () => {
                    // Update event time range.
                    // NB: Converting the datetimes back from the event timezone to UTC
                    // and formatting them using the server datetime format for save.
                    const formatForSave = (dt) => serializeDateTime(dt.setZone(eventTz, { keepLocalTime: true }));
                    await this.orm.write("event.event", [eventId], {
                        date_begin: formatForSave(newEventStart),
                        date_end: formatForSave(newEventEnd),
                    });
                    // Update the calendar event date range overlay.
                    this.model.data.event.start = newEventStart;
                    this.model.data.event.end = newEventEnd;
                    // Allow slots creation.
                    resolve(true);
                },
                cancel: () => resolve(false),
            });
        });
    }

    /**
     * @override
     * On mobile:
     * - Rename quick create dialog.
     * - Ask for confirmation when user tries to create slots outside of the event time range.
     */
    getQuickCreateFormViewProps(record) {
        return {
            ...super.getQuickCreateFormViewProps(record),
            onRecordSave: async (record) => {
                const slotStartTime = parseTime(formatFloatTime(record.data.start_hour), false);
                const slotEndTime = parseTime(formatFloatTime(record.data.end_hour), false);
                return this.checkAndConfirmSlotsCreation([record.data.date], slotStartTime, slotEndTime)
                    .then(async (canCreate) => {
                        if (canCreate) {
                            const saved = await record.save({ reload: false });
                            await this.model.load();
                            return saved;
                        }
                        return false;
                    });
            },
            title: _t("New Slot"),
        };
    }

    onClickAddButton() {
        this.action.doAction(
            {
                type: "ir.actions.act_window",
                name: _t("New Slot"),
                res_model: "event.slot",
                views: [[false, "form"]],
                target: "new",
            },
            {
                additionalContext: this.props.context,
                onClose: () => this.model.load(),
            }
        );
    }

    /**
     * @override
     * On desktop multi create mode:
     * - Ask for confirmation when user tries to create slots outside of the event time range.
     */
    onMultiCreate(multiCreateData, selectedCells) {
        const dates = this.getDates(selectedCells);
        const timeRange = multiCreateData.timeRange;
        this.checkAndConfirmSlotsCreation(dates, timeRange.start, timeRange.end).then((canCreate) => {
            if (canCreate) {
                this.model.multiCreateRecords(multiCreateData, dates);
            }
        });
    }
}
