/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { CalendarSidePanel } from "@web/views/calendar/calendar_side_panel/calendar_side_panel";
import { onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

patch(CalendarSidePanel.prototype, {
    setup() {
        super.setup(...arguments);
        this.orm = useService("orm");
        this.action = useService("action");
        this.holidayState = useState({
            monthHolidays: [],
            nextHoliday: null,
            loadedKey: null,
            loading: false,
        });

        onWillStart(async () => {
            if (this.showHolidayPanel) {
                await this.loadMonthHolidays();
            }
        });

        onWillUpdateProps(async () => {
            if (this.showHolidayPanel) {
                await this.loadMonthHolidays();
            }
        });
    },

    get showHolidayPanel() {
        if (!this.showDatePicker) {
            return false;
        }
        const resModel = this.props.model?.resModel || this.env.config?.resModel;
        // Never display public holidays panel on assignment or exam deadline pages
        if (!resModel || resModel === "university.assignment" || resModel.startsWith("university.assignment.")) {
            return false;
        }
        // Only show on the holiday and notice-board calendars. Student assignment
        // and timetable calendars must not display this extra public-holiday panel.
        const allowedModels = [
            "university.notice.board",
            "public.holiday",
            "university.holiday",
        ];
        return allowedModels.includes(resModel);
    },

    async loadMonthHolidays() {
        if (!this.showHolidayPanel || !this.props.model || !this.props.model.date) {
            return;
        }
        const currentDate = this.props.model.date;
        const currentKey = `${currentDate.year}-${String(currentDate.month).padStart(2, "0")}`;
        if (this.holidayState.loadedKey === currentKey && !this.holidayState.loading) {
            return;
        }

        this.holidayState.loading = true;
        try {
            const startOfMonth = currentDate.startOf("month").toISODate();
            const endOfMonth = currentDate.endOf("month").toISODate();

            const holidays = await this.orm.searchRead(
                "public.holiday",
                [
                    ["active", "=", true],
                    ["date_from", "<=", endOfMonth],
                    ["date_to", ">=", startOfMonth],
                ],
                ["id", "name", "name_km", "date_from", "date_to", "number_of_days", "status", "notice_id"],
                { order: "date_from asc, id asc" }
            );

            this.holidayState.monthHolidays = holidays;
            this.holidayState.loadedKey = currentKey;

            if (!holidays.length) {
                const next = await this.orm.searchRead(
                    "public.holiday",
                    [
                        ["active", "=", true],
                        ["date_from", ">", endOfMonth],
                    ],
                    ["id", "name", "name_km", "date_from", "date_to", "number_of_days"],
                    { order: "date_from asc", limit: 1 }
                );
                this.holidayState.nextHoliday = next.length ? next[0] : null;
            } else {
                this.holidayState.nextHoliday = null;
            }
        } catch (error) {
            console.error("Error loading calendar side panel public holidays:", error);
            this.holidayState.monthHolidays = [];
        } finally {
            this.holidayState.loading = false;
        }
    },

    formatHolidayDate(holiday) {
        if (!holiday || !holiday.date_from) return "";
        const fromDt = this.props.model.date.constructor.fromISO(holiday.date_from);
        const toDt = holiday.date_to ? this.props.model.date.constructor.fromISO(holiday.date_to) : fromDt;
        if (holiday.date_from === holiday.date_to || !holiday.date_to) {
            return fromDt.toFormat("LLL dd");
        }
        if (fromDt.month === toDt.month) {
            return `${fromDt.toFormat("LLL dd")} - ${toDt.toFormat("dd")}`;
        }
        return `${fromDt.toFormat("LLL dd")} - ${toDt.toFormat("LLL dd")}`;
    },

    isHolidayToday(holiday) {
        const todayStr = this.props.model.date.constructor.now().toISODate();
        const endStr = holiday.date_to || holiday.date_from;
        return holiday.date_from <= todayStr && endStr >= todayStr;
    },

    isHolidaySelected(holiday) {
        if (!this.props.model.date) return false;
        const selectedStr = this.props.model.date.toISODate();
        const endStr = holiday.date_to || holiday.date_from;
        return holiday.date_from <= selectedStr && endStr >= selectedStr;
    },

    get activeMonthName() {
        return this.props.model.date ? this.props.model.date.toFormat("LLLL yyyy") : "";
    },

    onHolidayClick(holiday) {
        if (holiday.date_from && this.props.model && this.props.model.load) {
            const date = this.props.model.date.constructor.fromISO(holiday.date_from);
            this.props.model.load({ date, scale: "day" });
        }
    },

    openNotice(noticeId, ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const id = Array.isArray(noticeId) ? noticeId[0] : noticeId;
        if (this.action && id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "university.notice.board",
                res_id: id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },

    openHoliday(holidayId, ev) {
        ev.stopPropagation();
        ev.preventDefault();
        const id = Array.isArray(holidayId) ? holidayId[0] : holidayId;
        if (this.action && id) {
            this.action.doAction({
                type: "ir.actions.act_window",
                res_model: "public.holiday",
                res_id: id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    },
});
