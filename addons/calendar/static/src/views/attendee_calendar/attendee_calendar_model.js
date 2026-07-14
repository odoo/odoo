/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { askRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import { deleteConfirmationMessage, ConfirmationDialog } from "@web/core/confirmation_dialog/confirmation_dialog";

export class AttendeeCalendarModel extends CalendarModel {
    setup(params, { dialog }) {
        super.setup(...arguments);
        this.dialog = dialog;
        this.rpc = rpc;
    }

    /**
     * @override
     */
    async load() {
        const res = await super.load(...arguments);
        const [credentialStatus, syncStatus, defaultDuration] = await Promise.all([
            rpc("/calendar/check_credentials"),
            this.orm.call("res.users", "check_synchronization_status", [[user.userId]]),
            this.orm.call("calendar.event", "get_default_duration"),
        ]);
        this.syncStatus = syncStatus;
        this.credentialStatus = credentialStatus;
        this.defaultDuration = defaultDuration;
        return res;
    }

    get attendees() {
        return this.data.attendees;
    }

    /**
     * @override
     *
     * Upon updating a record with recurrence, we need to ask how it will affect recurrent events.
     */
    async updateRecord(record) {
        const rec = this.records[record.id];
        if (rec.rawRecord.recurrency) {
            const recurrenceUpdate = await askRecurrenceUpdatePolicy(this.dialog);
            if (!recurrenceUpdate) {
                return this.notify();
            }
            record.recurrenceUpdate = recurrenceUpdate;
        }
        return await super.updateRecord(...arguments);
    }

    /**
     * @override
     */
    buildRawRecord(partialRecord, options = {}) {
        const result = super.buildRawRecord(partialRecord, {
            ...options,
            duration_hour: this.defaultDuration,
        });
        if (partialRecord.recurrenceUpdate) {
            result.recurrence_update = partialRecord.recurrenceUpdate;
        }
        return result;
    }

    /**
     * Load the filter section and add both 'user' and 'everybody' filters to the context.
     * @override
     */
    async loadFilterSection(fieldName, filterInfo, previousSection) {
        let result = await super.loadFilterSection(fieldName, filterInfo, previousSection);
        if (result?.filters) {
            user.updateContext({
                calendar_filters: {
                    all: result?.filters?.find((f) => f.type == "all")?.active ?? false,
                    user: result?.filters?.find((f) => f.type == "user")?.active ?? false,
                }
            });
        }
        return result;
    }

    /**
     * @override
     */
    async updateData(data) {
        await super.updateData(...arguments);
        await this.updateAttendeeData(data);
    }

    /**
     * Split the events to display an event for each attendee with the correct status.
     * If the all filter is activated, we don't display an event for each attendee and keep
     * the previous behavior to display a single event.
     */
    async updateAttendeeData(data) {
        const attendeeFilters = data.filterSections.partner_ids;
        let isEveryoneFilterActive = false;
        let attendeeIds = [];
        const eventIds = Object.keys(data.records).map((id) => Number.parseInt(id));
        if (attendeeFilters) {
            const allFilter = attendeeFilters.filters.find((filter) => filter.type === "all");
            isEveryoneFilterActive = (allFilter && allFilter.active) || false;
            attendeeIds = attendeeFilters.filters
                .filter((filter) => filter.type !== "all" && filter.value)
                .map((filter) => filter.value);
        }
        data.attendees = await this.orm.call("res.partner", "get_attendee_detail", [
            attendeeIds,
            eventIds,
        ]);
        const currentPartnerId = user.partnerId;
        if (!isEveryoneFilterActive) {
            const activeAttendeeIds = new Set(
                attendeeFilters.filters
                    .filter((filter) => filter.type !== "all" && filter.value && filter.active)
                    .map((filter) => filter.value)
            );
            // Duplicate records per attendee
            const newRecords = {};
            let duplicatedRecordIdx = -1;
            for (const event of Object.values(data.records)) {
                const eventData = event.rawRecord;
                const attendees =
                    eventData.partner_ids && eventData.partner_ids.length
                        ? eventData.partner_ids
                        : [eventData.partner_id[0]];
                let duplicatedRecords = 0;
                for (const attendee of attendees) {
                    if (!activeAttendeeIds.has(attendee)) {
                        continue;
                    }
                    // Records will share the same rawRecord.
                    const record = { ...event };
                    const attendeeInfo = data.attendees.find(
                        (a) => a.id === attendee && a.event_id === event.id
                    );
                    record.attendeeId = attendee;
                    // Colors are linked to the partner_id but in this case we want it linked
                    // to attendeeId
                    record.colorIndex = attendee;
                    if (attendeeInfo) {
                        record.attendeeStatus = attendeeInfo.status;
                        record.isAlone = attendeeInfo.is_alone;
                        record.isCurrentPartner = attendeeInfo.id === currentPartnerId;
                        record.calendarAttendeeId = attendeeInfo.attendee_id;
                    }
                    const recordId = duplicatedRecords ? duplicatedRecordIdx-- : record.id;
                    // Index in the records
                    record._recordId = recordId;
                    newRecords[recordId] = record;
                    duplicatedRecords++;
                }
            }
            data.records = newRecords;
        } else {
            for (const event of Object.values(data.records)) {
                const eventData = event.rawRecord;
                event.attendeeId = eventData.partner_id && eventData.partner_id[0];
                const attendeeInfo = data.attendees.find(
                    (a) => a.id === currentPartnerId && a.event_id === event.id
                );
                if (attendeeInfo) {
                    event.isAlone = attendeeInfo.is_alone;
                    event.calendarAttendeeId = attendeeInfo.attendee_id;
                }
            }
        }
    }

    /**
     * Archives a record, ask for the recurrence update policy in case of recurrent event.
     */
    async archiveRecord(record) {
        let recurrenceUpdate = false;
        if (record.rawRecord.recurrency) {
            recurrenceUpdate = await askRecurrenceUpdatePolicy(this.dialog);
            if (!recurrenceUpdate) {
                return;
            }
        } else {
            const confirm = await new Promise((resolve) => {
                this.dialog.add(
                    ConfirmationDialog,{
                        title: _t("Bye-bye, record!"),
                        body: deleteConfirmationMessage,
                        confirm: resolve.bind(null, true),
                        confirmLabel: _t("Delete"),
                        cancel: () => resolve.bind(null, false),
                        cancelLabel: _t("No, keep it"),
                    });
            });
            if (!confirm) {
                return;
            }
        }
        await this._archiveRecord(record.id, recurrenceUpdate);
    }

    async _archiveRecord(id, recurrenceUpdate) {
        if (!recurrenceUpdate && recurrenceUpdate !== "self_only") {
            await this.orm.call(this.resModel, "action_archive", [[id]]);
        } else {
            await this.orm.call(this.resModel, "action_mass_archive", [[id], recurrenceUpdate]);
        }
        await this.load();
    }
}
AttendeeCalendarModel.services = [...CalendarModel.services, "dialog", "orm"];
