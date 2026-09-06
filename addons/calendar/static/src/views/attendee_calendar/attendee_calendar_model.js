import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
import { useService } from "@web/core/utils/hooks";
import { CalendarModel } from "@web/views/calendar/calendar_model";
import { askRecurrenceUpdatePolicy } from "@calendar/views/ask_recurrence_update_policy_hook";
import {
    deleteConfirmationMessage,
    ConfirmationDialog,
} from "@web/core/confirmation_dialog/confirmation_dialog";
import { unique } from "@web/core/utils/arrays";

export class AttendeeCalendarModel extends CalendarModel {
    static services = [...CalendarModel.services, "dialog", "orm"];

    setup(params, services) {
        // fields needed for the duplicate feature and the popover
        const extraFields = ["partner_ids", "partner_id", "privacy", "user_can_edit", "recurrency"];
        params.fieldNames = unique(params.fieldNames.concat(extraFields));
        super.setup(...arguments);
        this.action = useService("action");
        this.dialog = services.dialog;
        this.rpc = rpc;
    }

    /**
     * @override
     */
    async load() {
        const res = await super.load(...arguments);
        if (!this._loaded) {
            const { credential_status, sync_status, sync_email, default_duration } =
                await this.orm.call("res.users", "get_calendar_model_data");
            this.syncStatus = sync_status;
            this.credentialStatus = credential_status;
            this.syncEmail = sync_email;
            this.defaultDuration = default_duration;
            this._loaded = true;
        }
        return res;
    }

    get attendees() {
        return this.data.attendees;
    }

    /**
     * @override
     */
    getBaseDomain() {
        const baseDomain = super.getBaseDomain();
        if (!this.meta.context?.calendar_include_user_events || !baseDomain.length) {
            return baseDomain;
        }
        return Domain.or([baseDomain, [["partner_ids", "in", [user.partnerId]]]]).toList();
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
        const result = await super.loadFilterSection(fieldName, filterInfo, previousSection);
        if (result?.fieldName === "calendar_id") {
            result?.filters?.forEach(f => {
                if (f.isPrimary) {
                    // reuse existing canRemove field on parent component
                    f.canRemove = false;
                }
            });
        }
        if (result?.fieldName === "partner_ids") {
            if (result?.filters) {
                user.updateContext({
                    calendar_filters: {
                        all: result?.filters?.find((f) => f.type === "all")?.active ?? false,
                        user: result?.filters?.find((f) => f.type === "user")?.active ?? false,
                    },
                });
            }
            result.filters = result?.filters?.filter(f => f.type !== "user");
        }
        return result;
    }

    /**
     * @override
     * Normally, the filters use the AND operator to combine the domains.
     * However, we want show events which match either of the filters,
     * so we need to OR the domains instead
     */
    computeFiltersDomain(data) {
        const filteredData = {...data, filterSections: Object.fromEntries(
            Object.entries(data.filterSections ?? {}).filter(([key]) => key !== "partner_ids" && key !== "calendar_id")
        )};
        const domain = super.computeFiltersDomain(filteredData);
        const partnerFilters = data.filterSections['partner_ids']?.filters || [];
        const activePartnerIds = partnerFilters.filter(f => f.active).map(f => f.value);
        const calendarFilters = data.filterSections['calendar_id']?.filters || [];
        const activeCalendarIds = calendarFilters.filter(f => f.active).map(f => f.value);
        const primaryCalendarFilter = calendarFilters.find(f => f.isPrimary);
        const includesPrimaryCalendar = primaryCalendarFilter?.active ?? false;
        const filterDomains = [['|', ["calendar_id", "in", activeCalendarIds], ["partner_ids", "in", activePartnerIds]]];

        // If the primary calendar is checked, include events the user
        // is attending which are not in any of their calendars.
        if (includesPrimaryCalendar) {
            filterDomains.push([
            "&",
                ["partner_ids", "in", [user.partnerId]],
                ["calendar_id", "not in", this.calendarIds ?? []],
            ]);
        }
        return Domain.and([domain, Domain.or(filterDomains)]).toList();
    }

    /**
     * @override
     */
    async updateData(data) {
        if (!this._loaded) {
            const userData = await this.orm.read("res.users", [user.userId], ["calendar_ids"])
            this.calendarIds = userData[0]?.calendar_ids
        }
        await super.updateData(...arguments);
        await this.updateAttendeeData(data);
    }

    getActivePartnerIds(data) {
        const attendeeFilters = (data.filterSections.partner_ids?.filters || [])
            .filter((filter) => filter.value && filter.active)
            .map((filter) => filter.value)

        const primaryCalendarFilter = data.filterSections.calendar_id?.filters?.find(c => c.isPrimary);
        if (primaryCalendarFilter?.active && !attendeeFilters.includes(user.partnerId)) {
            return [user.partnerId, ...attendeeFilters];
        } else {
            return attendeeFilters;
        }
    }

    /**
     * Split the events to display an event for each attendee with the correct status.
     * If the all filter is activated, we don't display an event for each attendee and keep
     * the previous behavior to display a single event.
     *
     * If any calendar filters are activated, we consider the current user as an attendee
     * even if they are not selected in the attendee filters.
     */
    async updateAttendeeData(data) {
        const attendeeFilters = data.filterSections.partner_ids;
        const calendarFilters = data.filterSections.calendar_id;
        const currentPartnerId = user.partnerId;
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
        // If we show events based on calendar filters, we want to get the current
        // user's attendee data even if they are not selected in attendee filters
        if (calendarFilters && calendarFilters.filters.some((filter) => filter.active)
            && !attendeeIds.includes(currentPartnerId)) {
            attendeeIds.push(currentPartnerId);
        }
        data.attendees = await this.orm.call("res.partner", "get_attendee_detail", [
            attendeeIds,
            eventIds,
        ]);
        if (!isEveryoneFilterActive && attendeeFilters) {
            const activeAttendeeIds = new Set(this.getActivePartnerIds(data));
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
                    // Records which are fetched based on the calendar filters should match calendar colors
                    if (attendee !== user.partnerId) {
                        // If a color doesn't belong to the user's calendar, it is instead based on the attendeeId
                        record.colorIndex = attendee;
                    }
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
                // The method directly sets the data.records based on the attendee data. With the inclusion
                // of calendar filters, we may display events that the user is not attending if they are in
                // their calendar. These also have to be included in the final data.records.
                if (duplicatedRecords === 0) {
                    newRecords[event.id] = event
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
                this.dialog.add(ConfirmationDialog, {
                    title: _t("Bye-bye, record!"),
                    body: deleteConfirmationMessage,
                    confirm: resolve.bind(null, true),
                    confirmLabel: _t("Delete"),
                    confirmClass: "btn-danger",
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

    normalizeRecord(rawRecord) {
        const normalizedRecord = super.normalizeRecord(rawRecord);
        if (rawRecord.effective_privacy === "private") {
            normalizedRecord.titleIcon = "lock";
        }
        if (rawRecord['calendar_color']) {
            normalizedRecord.colorIndex = rawRecord['calendar_color'];
        }
        return normalizedRecord;
    }

    /**
     * @override
     */
    makeFilterRecord(filterInfo, previousFilter, rawRecord) {
        let filterRecord = super.makeFilterRecord(...arguments);
        // update the filter color
        const { colorFieldName } = filterInfo;
        const colorValue = rawRecord[colorFieldName]
        if (colorValue) {
            filterRecord.colorIndex = colorValue;
        } else if (rawRecord.partner_id) {
            filterRecord.colorIndex = rawRecord.partner_id[0];
        }
        // Add flags to calendar filters
        if (rawRecord['access_role']) {
            filterRecord['accessRole'] = rawRecord['access_role'];
        }
        if (rawRecord['is_primary']) {
            filterRecord['isPrimary'] = rawRecord['is_primary'];
        }
        return filterRecord;
    }

    /**
     * @override
     */
    fetchFilters(resModel, fieldNames) {
        if (resModel !== 'calendar.user') {
            return super.fetchFilters(...arguments);
        }
        return this.orm.searchRead(resModel,
            [["user_id", "=", user.userId], ["is_filter_active", "=", true]],
            [...fieldNames, 'is_primary', 'access_role', 'filter_color']
        );
    }

    /**
     * @override
     */
    async unlinkFilter(fieldName, recordId) {
        if (fieldName !== 'calendar_id') {
            return super.unlinkFilter(...arguments);
        }
        const info = this.meta.filtersInfo[fieldName];
        const section = this.data.filterSections[fieldName];
        if (section) {
            // remove the filter directly, to provide direct feedback to the user
            this.keepLast.add(Promise.resolve());
            section.filters = section.filters.filter((f) => f.recordId !== recordId);
        }
        if (info && info.writeResModel) {
            // The model holding the filter values also holds other information about user access.
            // Instead of unlinking the model, we just deactivate the filter.
            await this.orm.write(info.writeResModel, [recordId], {"is_filter_active": false});
            await this.debouncedLoad();
        }
    }
}
