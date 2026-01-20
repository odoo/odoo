import { CalendarController } from "@web/views/calendar/calendar_controller";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useEffect } from "@odoo/owl";
import {
    getEndOfLocalWeek,
    getLocalYearAndWeek,
    getStartOfLocalWeek,
    serializeDate,
} from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class ResourceCalendarAttendanceCalendarController extends CalendarController {
    static template = "resource.ResourceCalendarAttendanceCalendarController";
    static components = {
        ...CalendarController.components,
        Dropdown,
        DropdownItem,
    };

    setup() {
        super.setup();
        this.dialogService = useService("dialog");
        this.state.lastPeriods = [];
        useEffect(
            (nextStart) => {
                this.state.lastPeriods = this.updateLastPeriods(nextStart);
            },
            () => [this.model.visibleRange.start]
        );
    }

    updateLastPeriods(nextStart) {
        const lastPeriods = [];
        if (this.model.scale === "week") {
            for (let i = 1; i <= 5; i++) {
                const newDate = nextStart.minus({weeks: i});
                const start = getStartOfLocalWeek(newDate);
                const end = getEndOfLocalWeek(newDate);
                lastPeriods.push({
                    date: newDate,
                    string: _t("Week %(weekNumber)s %(year)s: %(start)s - %(end)s", {
                        start: start.toFormat("MMM dd"),
                        end: end.toFormat("MMM dd"),
                        year: newDate.year,
                        weekNumber: getLocalYearAndWeek(newDate).week,
                    }),
                });
            }
        }
        return lastPeriods;
    }

    async _copyFrom(sourceDate, targetDate) {
        const res = await this.orm.call("resource.calendar", "copy_from", [
            [this.props.context.default_calendar_id],
            serializeDate(sourceDate),
            serializeDate(targetDate),
        ]);
        if (!res) {
            this.dialogService.add(ConfirmationDialog, {
                title: _t("Conflict"),
                body: _t(
                    "The target week is not empty. Continuing will permanently erase the current schedules for this period." +
                        "\nDo you want to proceed?"),
                confirmLabel: _t("Proceed"),
                confirm: async () => {
                    await this.orm.call("resource.calendar", "copy_from", [
                        [this.props.context.default_calendar_id],
                        serializeDate(sourceDate),
                        serializeDate(targetDate),
                        true,
                    ]);
                    return this.model.load();
                },
                cancelLabel: _t("Cancel"),
                cancel: () => {},
            });
        } else {
            return this.model.load();
        }
    }

    async onCopyFrom(date) {
        await this._copyFrom(date, this.model.visibleRange.start);
    }
}
