/** @odoo-module **/

import { CalendarModel } from "@web/views/calendar/calendar_model";
import {
    serializeDate,
    serializeDateTime,
    deserializeDate,
    deserializeDateTime,
} from "@web/core/l10n/dates";

/**
 * CalendarModel allowing the usage of properties as calendar options.
 * Note: currently, as it is only used in knowledge, the properties
 * field name has been hardcoded for clarity, but if needed it can be
 * easily retrieved from the archInfo.
 */
export class ItemCalendarModel extends CalendarModel {

    /**
     * @override
     * Prevent creation of record if the user does not have write access on the
     * parent record (readonly knowledge articles for example) and if the model
     * props are invalid
     */
    get canCreate() {
        if (this.meta.invalid) {
            return false;
        }
        return this.meta.canCreate;
    }
    /**
     * @override
     * Usually, records cannot be edited if the start field is readonly (which
     * is a property shared by every record of the current calendar). In this
     * case however, it depends on the record (eg. users cannot edit readonly
     * knowledge articles). Therefore, we always allow users to edit the record
     * but we show an access error if the user tried to edit a readonly record.
     */
    get canEdit() {
        return true;
    }

    /**
     * @override
     * Show the "all day" slot in "day" and "week" scales even if the date is a
     * datetime, as there is no "allDay" option in this model.
     */
    get hasAllDaySlot() {
        return true;
    }

    /**
     * @override
     * Build a raw record from the given partial record and the properties. We
     * need every property of the record when editing a record otherwise we 
     * will lose the values of these properties when writing on the record
     * (since the properties are stored as json objects).
     */
    buildRawRecord(partialRecord, options = {}) {
        let start = partialRecord.start;
        let end = partialRecord.end;

        if (!end || !end.isValid) {
            // Set end date if not existing
            if (this.meta.propertiesDateType === "date") {
                end = start;
            } else {
                end = start.plus({ hours: 1 });
            }
        }

        if (this.meta.propertiesDateType === "datetime" && partialRecord.isAllDay) {
            if (partialRecord.id) {
                // Keep time of the record when moving or resizing a datetime
                // record in an allDay scale (eg. in month scale, there is no
                // time scale so the partialRecord is created as an allDay
                // record even if the record moved it is a datetime)
                start = start.set({ hours: this.data.records[partialRecord.id].start.hour});
                end = end.set({ hours: this.data.records[partialRecord.id].end.hour });  
            } else {
                // When creating a datetime that spans multiple days, set
                // arbitrary start and end hours (to not have midnight by
                // default)
                start = start.set({hours: 7});
                end = end.set({hours: 19});
            }
        }

        start = this.meta.propertiesDateType === "date" ? serializeDate(start) : serializeDateTime(start);
        end = this.meta.propertiesDateType === "date" ? serializeDate(end) : serializeDateTime(end);

        let properties = {};

        if (partialRecord.id) {
            // Copy the properties of the existing rawRecord but update the
            // start and stop date properties
            properties = this.data.records[partialRecord.id].rawRecord.article_properties;
            properties.find(property => property.name === this.meta.fieldMapping.date_start).value = start;

            if (this.meta.fieldMapping.date_stop) {
                properties.find(property => property.name === this.meta.fieldMapping.date_stop).value = end;
            }
        } else {
            // Create the start and stop date properties for the new record
            properties[this.meta.fieldMapping.date_start] = start;
            if (this.meta.fieldMapping.date_stop) {
                properties[this.meta.fieldMapping.date_stop] = end;
            }
        }
        return {article_properties: properties};
    }

    /**
     * If the model is invalid (missing props needed to fetch the correct
     * items after a reload for example), no record should be loaded.
     */
    loadRecords(data) {
        if (this.meta.invalid) {
            return {};
        }
        return super.loadRecords(data);
    }

    /**
     * @override
     * Normalize the given raw record with the properties
     */
    normalizeRecord(rawRecord) {
        const { fieldMapping, propertiesDateType, scale } = this.meta;
        const isDate = propertiesDateType === "date";

        const startValue = rawRecord.article_properties.find(property => property.name === fieldMapping.date_start)?.value;
        const stopValue = rawRecord.article_properties.find(property => property.name === fieldMapping.date_stop)?.value;
        const start = isDate
            ? deserializeDate(startValue)
            : deserializeDateTime(startValue);

        // If the stop property is not set, use the same date as the start
        // to not show an invalid date message
        const end = stopValue ?
            isDate
                ? deserializeDate(stopValue)
                : deserializeDateTime(stopValue)
            : start;

        // The time of the record is shown in the calendar if it is a datetime
        // and if the selected scale is month (because there is no time scale
        // in this case)
        const showTime = scale === "month" && !isDate;
            
        const colorValue = rawRecord.article_properties.find(property => property.name === fieldMapping.color)?.value;
        const colorIndex = Array.isArray(colorValue) ? colorValue[0] : colorValue;

        return {
            id: rawRecord.id,
            title: rawRecord.display_name,
            isAllDay: isDate,
            start,
            startType: propertiesDateType,
            end,
            endType: propertiesDateType,
            colorIndex,
            isTimeHidden: !showTime,
            rawRecord,
        };
    }

    /**
     * @override
     * Compute the domain used to fetch the items using the properties used as
     * start and end date. The properties definition is used in the domain to
     * make sure to not match records that still use the "previous" dateStart
     * property when this property has been changed (if the type of a property
     * changed, the property will be replaced by a new one but the change will
     * be propagated to the records using that property when writing on them)
     */
    computeRangeDomain(data) {
        const { fieldMapping } = this.meta;
        const formattedEnd = serializeDateTime(data.range.end);
        const formattedStart = serializeDateTime(data.range.start);

        const domain = [
            [`article_properties.${fieldMapping.date_start}`, "<=", formattedEnd],
            ['parent_id.article_properties_definition', 'ilike', `"${fieldMapping.date_start}"`]
        ];
        if (fieldMapping.date_stop) {
            domain.push(
                [`article_properties.${fieldMapping.date_stop}`, ">=", formattedStart],
                ['parent_id.article_properties_definition', 'ilike', `"${fieldMapping.date_stop}"`]
            );
        }
        return domain;
    }
}
