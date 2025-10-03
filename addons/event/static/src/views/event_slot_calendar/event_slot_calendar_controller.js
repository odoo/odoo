import { CalendarController } from "@web/views/calendar/calendar_controller";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { formatFloatTime } from "@web/views/fields/formatters";
import { parseTime } from "@web/core/l10n/time";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

const { DateTime } = luxon;

export class EventSlotCalendarController extends CalendarController {
    static template = "event.EventSlotCalendarController";

    setup() {
        super.setup();
        this.actionService = useService("action");
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
        const { start: eventStartStr, end: eventEndStr, tz: eventTz } = this.model.data.event || {};
        if (!eventStartStr || !eventEndStr || !eventTz || !slotDates?.length || !slotStart || !slotEnd) {
            return true;
        }
        // Check if slots are within the event time range.
        // NB: Event and slot datetimes are already in the event timezone.
        const serverDatetimeFormat = 'yyyy-MM-dd HH:mm:ss';
        const eventStartDatetime = DateTime.fromFormat(eventStartStr, serverDatetimeFormat);
        const eventEndDatetime = DateTime.fromFormat(eventEndStr, serverDatetimeFormat);
        let earliestSlotStart = null;
        let latestSlotEnd = null;
        for (const date of slotDates) {
            const start = date.plus(slotStart.toObject());
            const end = date.plus(slotEnd.toObject());
            if (start < eventStartDatetime) {
                earliestSlotStart = earliestSlotStart ? DateTime.min(earliestSlotStart, start) : start;
            }
            if (eventEndDatetime < end) {
                latestSlotEnd = latestSlotEnd ? DateTime.max(latestSlotEnd, end) : end;
            }
        }
        if (!earliestSlotStart && !latestSlotEnd) {
            return true;
        }
        // Some slots are out of event time range, ask for confirmation to extend the range.
        return await new Promise((resolve) => {
            this.dialogService.add(ConfirmationDialog, {
                title: _t("Confirmation"),
                body: _t(
                    "Adding these slots will automatically adjust the event's time range to include them.\n\n" +
                    "From:\t%(start)s - %(end)s\n" +
                    "To:\t\t%(new_start)s - %(new_end)s\n" +
                    "\t\t(%(tz)s)"
                , {
                    start: eventStartDatetime.toLocaleString(DateTime.DATETIME_MED),
                    end: eventEndDatetime.toLocaleString(DateTime.DATETIME_MED),
                    new_start: (earliestSlotStart || eventStartDatetime).toLocaleString(DateTime.DATETIME_MED),
                    new_end: (latestSlotEnd || eventEndDatetime).toLocaleString(DateTime.DATETIME_MED),
                    tz: eventTz,
                }),
                confirmLabel: _t("Update Event"),
                confirm: async () => {
                    const formatForSave = (dt) => dt.setZone(eventTz, { keepLocalTime: true }).toUTC().toFormat(serverDatetimeFormat);
                    // Update event time range.
                    await this.orm.write("event.event", [this.props.context.default_event_id], {
                        ...(earliestSlotStart && { date_begin: formatForSave(earliestSlotStart) }),
                        ...(latestSlotEnd && { date_end: formatForSave(latestSlotEnd) }),
                    });
                    // Update the calendar event date range overlay.
                    this.model.data.event.start = (earliestSlotStart || eventStartDatetime).toFormat(serverDatetimeFormat);
                    this.model.data.event.end = (latestSlotEnd || eventEndDatetime).toFormat(serverDatetimeFormat);
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

    /**
     * On mobile and desktop:
     * - Add a "New" button for single record creation.
     * - Raise validation error if slot is outside of the event time range.
     */
    onClickAddButton() {
        this.actionService.doAction(
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
