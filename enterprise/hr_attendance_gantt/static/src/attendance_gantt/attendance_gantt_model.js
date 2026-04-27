import { serializeDateTime } from "@web/core/l10n/dates";
import { GanttModel, parseServerValues } from "@web_gantt/gantt_model";
import { Domain } from "@web/core/domain";

export class AttendanceGanttModel extends GanttModel {
    //-------------------------------------------------------------------------
    // Protected
    //-------------------------------------------------------------------------

    /**
     * @override
     */
    _getDomain(metaData) {
        const { dateStartField, dateStopField, globalStart, globalStop } = metaData;
        const dateNow = luxon.DateTime.now();
        if (dateNow >= globalStart) {
            const domain = Domain.and([
                this.searchParams.domain,
                [
                    "&",
                    [dateStartField, "<", serializeDateTime(globalStop)],
                    "|",
                    "&",
                    [dateStartField, "<", serializeDateTime(dateNow)],
                    [dateStopField, "=", false],
                    [dateStopField, ">", serializeDateTime(globalStart)],
                ],
            ]);
            return domain.toList();
        } else {
            return super._getDomain(...arguments);
        }
    }

    async _fetchData(metaData) {
        const startDate = metaData.globalStart.toISODate();
        let activeDomain = [];
        if (!this.searchParams.domain.some((index) => Array.isArray(index) && index[0] == "employee_id.active")){
            activeDomain.push(["employee_id.active", "=", true]);
        }
        const context = {
            gantt_start_date: startDate,
            user_domain: this.searchParams.domain,
            active_domain: activeDomain
        };
        await super._fetchData(metaData, context);
    }

    _parseServerData(metaData, records) {
        const { dateStartField, dateStopField, fields } = metaData;
        /** @type {Record<string, any>[]} */
        const parsedRecords = super._parseServerData(...arguments);
        for (const record of records) {
            const parsedRecord = parseServerValues(fields, record);
            const dateStart = parsedRecord[dateStartField];
            const dateStop = parsedRecord[dateStopField];
            if (!this.orm.isSample && dateStart && !dateStop) {
                parsedRecord[dateStopField] = luxon.DateTime.now();
                parsedRecords.push(parsedRecord);
            }
        }
        return parsedRecords;
    }
}
