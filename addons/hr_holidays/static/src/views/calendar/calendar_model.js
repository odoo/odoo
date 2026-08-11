import { CalendarModel } from "@web/views/calendar/calendar_model";
import {
    deserializeDate,
    deserializeDateTime,
    serializeDate,
    serializeDateTime,
} from "@web/core/l10n/dates";
import { Cache } from "@web/core/utils/cache";
import { ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

export class TimeOffCalendarModel extends CalendarModel {
    static services = [...CalendarModel.services, "dialog"];

    setup(params, services) {
        super.setup(params, services);

        this.dialog = services.dialog;
        this.data.mandatoryDays = {};
        if (this.uiService.isSmall) {
            this.meta.scale = "month";
        }

        this._mandatoryDaysCache = new Cache(
            (data) => this.fetchMandatoryDays(data),
            (data) => `${serializeDateTime(data.range.start)},${serializeDateTime(data.range.end)}`
        );
    }

    /**
     * @override
     */
    normalizeRecord(rawRecord) {
        const result = super.normalizeRecord(...arguments);
        if (rawRecord.employee_id) {
            const employee = rawRecord.employee_id[1];
            // If the employee's name isn't already included at the start of the title
            if (!result.title.startsWith(employee)) {
                result.title = [employee, result.title].join(" ");
            }
        }
        if (rawRecord.work_entry_type_request_unit === "half_day") {
            result.requestDateFromPeriod = rawRecord.request_date_from_period;
            result.requestDateToPeriod = rawRecord.request_date_to_period;
        }
        const states = Object.fromEntries(this.fields.state.selection);
        result.stateLabel = states[rawRecord.state];
        return result;
    }

    makeContextDefaults(record) {
        const context = super.makeContextDefaults(record);
        let default_employee_id = this.employeeId;
        if (context["active_model"] === "hr.employee") {
            default_employee_id = context.active_id;
        }
        if (default_employee_id) {
            context["default_employee_id"] = default_employee_id;
        }
        function deserialize(str) {
            // "YYYY-MM-DD".length == 10
            return str.length > 10 ? deserializeDateTime(str) : deserializeDate(str);
        }
        if (["week", "day"].includes(this.scale)) {
            context["default_work_entry_type_request_unit"] = "hour";
            const hour_from = deserialize(context["default_request_date_hour_from"] ?? this.date);
            const hour_to = deserialize(context["default_request_date_hour_to"] ?? this.date);
            context["default_request_hour_from"] = hour_from.hour + hour_from.minute / 60;
            context["default_request_hour_to"] = hour_to.hour + hour_to.minute / 60;
        }

        for (const [bound, hour] of [
            ["from", 7],
            ["to", 19],
        ]) {
            const key = `default_request_date_hour_${bound}`;
            if (key in context) {
                context[key] = serializeDateTime(deserialize(context[key]).set({ hours: hour }));
            }
        }
        return context;
    }

    /**
     * @override
     */
    get canEdit() {
        return this.meta.canEdit;
    }

    /**
     * @override
     * Reschedule an hr.leave drag/resize via a backend method that reads the endpoints
     * in the employee's timezone and snaps to the request unit. Rescheduling an approved
     * request needs re-approval, so confirm first; the backend then resets it to "To
     * Approve". A backend failure rejects so the renderer reverts the event.
     */
    async updateRecord(record, options = {}) {
        if (this.resModel !== "hr.leave") {
            return super.updateRecord(record, options);
        }
        const rawRecord = this.records[record.id]?.rawRecord;
        const needsReapproval =
            rawRecord &&
            ["validate", "validate1"].includes(rawRecord.state) &&
            rawRecord.validation_type !== "no_validation";
        if (!needsReapproval) {
            return this._rescheduleRecord(record);
        }
        return new Promise((resolve, reject) => {
            this.dialog.add(ConfirmationDialog, {
                title: _t("Confirmation"),
                body: _t(
                    "If you modify this request, it will need to be approved again. Do you wish to continue?"
                ),
                confirmLabel: _t("Confirm"),
                cancelLabel: _t("Discard"),
                confirm: async () => {
                    try {
                        await this._rescheduleRecord(record);
                        resolve();
                    } catch (error) {
                        // Re-throw so the renderer reverts the event and the error service shows the message.
                        reject(error);
                    }
                },
                // Discard: reload so the event snaps back to its original period.
                cancel: async () => {
                    await this.load();
                    resolve();
                },
            });
        });
    }

    async _rescheduleRecord(record) {
        const end = record.end?.isValid ? record.end : record.start;
        await this.orm.call(
            this.resModel,
            "reschedule_from_calendar",
            [[record.id], serializeDateTime(record.start), serializeDateTime(end)],
            { context: this.meta.context }
        );
        await this.load();
    }

    async updateData(data) {
        const prom = super.updateData(data);
        data.mandatoryDays = await this._mandatoryDaysCache.read(data);
        return prom;
    }

    /**
     * @override
     */
    fetchUnusualDays(data) {
        return this.orm.call(
            this.meta.resModel,
            "get_unusual_days",
            [serializeDateTime(data.range.start), serializeDateTime(data.range.end)],
            {
                context: {
                    employee_id: this.employeeId,
                },
            }
        );
    }

    async fetchMandatoryDays(data) {
        return this.orm.call("hr.employee", "get_mandatory_days", [
            this.employeeId,
            serializeDate(data.range.start, "datetime"),
            serializeDate(data.range.end, "datetime"),
        ]);
    }

    get mandatoryDays() {
        return this.data.mandatoryDays;
    }

    get employeeId() {
        return (
            (this.meta.context.employee_id && this.meta.context.employee_id[0]) ||
            (this.meta.context.active_model === "hr.employee" && this.meta.context.active_id) ||
            null
        );
    }

    fetchRecords(data) {
        const { fieldNames, resModel } = this.meta;
        const context = {};
        if (!this.employeeId) {
            context["short_name"] = 1;
        }
        const fieldNamesToAdd =
            resModel === "hr.leave"
                ? [
                      "work_entry_type_request_unit",
                      "request_date_from_period",
                      "request_date_to_period",
                      "state",
                      "validation_type",
                      "can_reschedule",
                  ]
                : [];
        return this.orm.searchRead(
            resModel,
            this.computeDomain(data),
            [...fieldNames, ...fieldNamesToAdd],
            { context }
        );
    }

    computeDomain(data) {
        return [...super.computeDomain(data), ["state", "!=", "cancel"]];
    }
}
