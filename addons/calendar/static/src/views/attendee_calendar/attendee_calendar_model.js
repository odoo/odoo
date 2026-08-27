import { Domain } from "@web/core/domain";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { user } from "@web/core/user";
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
        this.dialog = services.dialog;
        this.rpc = rpc;
        this.resetPartnerFilters = true;
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
        if (this.resetPartnerFilters) {
            this.resetPartnerFilters = false;
            await this.orm.call("calendar.filters", "init_user_filters", [], {
                context: this.meta.context,
            });
            await this.debouncedLoad();
        }
        return res;
    }

    get attendees() {
        return this.data.attendees;
    }
    get showMyCalendar() {
        return user.settings.calendar_show_my;
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

    async updateRecordFilters(fieldName, filters) {
        this.keepLast.add(Promise.resolve());
        const info = this.meta.filtersInfo[fieldName];
        if (info && info.writeFieldName && info.writeResModel && info.filterFieldName) {
            await this.orm.call(info.writeResModel, "update_user_filters", [filters]);
        }
        await this.debouncedLoad();
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
     * @override
     */
    computeFiltersDomain(data) {
        // List authorized values for every field
        // fields with an active "all" filter are skipped
        const authorizedValues = {};
        const avoidValues = {};

        for (const [fieldName, filterSection] of Object.entries(data.filterSections)) {
            const filterSectionInfo = this.meta.filtersInfo[fieldName];
            const field = this.meta.fields[fieldName];
            const isUserOrPartner = ["res.users", "res.partner"].includes(field.relation);
            const userFieldName = field.relation === "res.partner" ? "partnerId" : "userId";
            // Loop over subfilters to complete authorizedValues
            for (const filter of filterSection.filters) {
                if (filterSectionInfo.writeResModel) {
                    if (!authorizedValues[fieldName]) {
                        authorizedValues[fieldName] = [];
                    }
                    // Current user's partner is controlled separately by a checkbox linked to a setting
                    if (isUserOrPartner && filter.value === user[userFieldName]) {
                        continue;
                    }
                    if (filter.active) {
                        authorizedValues[fieldName].push(filter.value);
                    }
                } else {
                    if (!filter.active) {
                        if (!avoidValues[fieldName]) {
                            avoidValues[fieldName] = [];
                        }
                        avoidValues[fieldName].push(filter.value);
                    }
                }
            }
            if (filterSectionInfo.writeResModel && isUserOrPartner && this.showMyCalendar) {
                if (!authorizedValues[fieldName]) {
                    authorizedValues[fieldName] = [];
                }

                authorizedValues[fieldName].push(user[userFieldName]);
            }
        }

        // Compute the domain
        const domain = [];
        for (const field in authorizedValues) {
            domain.push([field, "in", authorizedValues[field]]);
        }
        for (const field in avoidValues) {
            if (avoidValues[field].length > 0) {
                domain.push([field, "not in", avoidValues[field]]);
            }
        }
        return domain;
    }

    /**
     * @override
     */
    makeContextDefaults(rawRecord) {
        const context = super.makeContextDefaults(rawRecord);
        const partnerSection = Object.values(this.data.filterSections).find(
            (section) => this.meta.fields[section.fieldName]?.relation === "res.partner"
        );

        if (partnerSection) {
            const partnerIds = partnerSection.filters
                .filter((filter) => filter.active && filter.type === "record")
                .map((filter) => filter.value);
            if (this.showMyCalendar) {
                partnerIds.push(user.partnerId);
            }
            context.default_partner_ids = [...new Set(partnerIds)];
        }
        return context;
    }

    /**
     * Load the filter section and add both 'user' and 'everybody' filters to the context.
     * @override
     */
    async loadFilterSection(fieldName, filterInfo, previousSection) {
        const result = await super.loadFilterSection(fieldName, filterInfo, previousSection);
        if (result?.filters) {
            user.updateContext({
                calendar_filters: {
                    all: result?.filters?.find((f) => f.type == "all")?.active ?? false,
                    user: result?.filters?.find((f) => f.type == "user")?.active ?? false,
                },
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
        if (!isEveryoneFilterActive && attendeeFilters) {
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
        return normalizedRecord;
    }
}
