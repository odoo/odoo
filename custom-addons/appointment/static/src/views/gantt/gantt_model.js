/** @odoo-module **/

import { Domain } from "@web/core/domain";
import { GanttModel } from "@web_gantt/gantt_model";

export class AppointmentBookingGanttModel extends GanttModel {
    /**
     * @override
     */
    load(searchParams) {
        // add some context keys to the search
        return super.load({
            ...searchParams,
            context: { ...searchParams.context, appointment_booking_gantt_show_all_resources: true }
        });
    }

    /**
     * Update the organizer of relevant events after updating attendees.
     *
     * @override
     */
    async reschedule(ids, schedule, callback) {
        if (
            !this.metaData.groupedBy ||
            this.metaData.groupedBy[0] !== "partner_ids" ||
            !schedule.partner_ids
        ) {
            return super.reschedule(...arguments);
        }

        if (!Array.isArray(ids)) {
            ids = [ids];
        }
        const idsToUpdate = this.data.records
            .filter(
                (record) =>
                    ids.includes(record.id) &&
                    ((record.partner_id?.length && schedule.originId === record.partner_id[0]) ||
                        !record.partner_id?.length),
            )
            .map((record) => record.id);
        const newUserId = this.orm
            .read("res.partner", [schedule.partner_ids[0]], ["user_ids"])
            .then((result) => (result[0]?.user_ids[0] ? result[0].user_ids[0] : false));

        const result = super.reschedule(ids, schedule, async (ormWriteResult) => {
            if (idsToUpdate.length && newUserId) {
                await this.orm.write("calendar.event", idsToUpdate, {
                    user_id: await newUserId,
                });
            }
            if (callback) {
                callback(ormWriteResult);
            }
        });

        return result;
    }

    /**
     * Replace the raw list of ids set by gantt by link and unlink commands
     * so that only the partner selected by the user changes instead of replacing
     * all partners with the new one.
     *
     * @override
     */
    _scheduleToData(schedule) {
        const data = super._scheduleToData(...arguments);

        if (!this.metaData.groupedBy || !schedule.originId) {
            return data;
        }
        if (
            this.metaData.groupedBy &&
            this.metaData.groupedBy[0] === "partner_ids" &&
            schedule.partner_ids &&
            data.partner_ids[0] !== schedule.originId // attendee_ids will be messed up without this check
        ) {
            return {
                ...data,
                partner_ids: [
                    [3, schedule.originId, 0],
                    [4, data.partner_ids[0], 0],
                ],
            };
        }
        if (
            this.metaData.groupedBy &&
            this.metaData.groupedBy[0] === "resource_ids" &&
            schedule.resource_ids &&
            data.resource_ids[0] !== schedule.originId
        ) {
            return {
                ...data,
                resource_ids: [
                    [3, schedule.originId, 0],
                    [4, data.resource_ids[0], 0],
                ],
            };
        }
        return data;
    }

    /**
     * @override
     */
    _getDomain(metaData) {
        const domainList = super._getDomain(metaData);
        const ganttDomain = this.searchParams.context.appointment_booking_gantt_domain;
        if (ganttDomain) {
            return Domain.and([domainList, ganttDomain]).toList();
        }
        return domainList;
    }
}
