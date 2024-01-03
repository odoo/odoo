/** @odoo-module */

import { models } from "@web/../tests/web_test_helpers";
import { capitalize } from "@web/core/utils/strings";

/**
 * @typedef {import("@web/../tests/web_test_helpers").ModelRecord} ModelRecord
 */

export class MailTrackingValue extends models.ServerModel {
    _name = "mail.tracking.value";

    /**
     * @override
     * @type {typeof models.Model["prototype"]["write"]}
     */
    write(idOrIds, values, kwargs) {
        const initialTrackedFieldValuesByRecordId = this.env["mail.thread"]._trackPrepare(
            this._name
        );
        const result = super.write(idOrIds, values, kwargs);
        if (initialTrackedFieldValuesByRecordId) {
            this.env["mail.thread"]._trackFinalize(this._name, initialTrackedFieldValuesByRecordId);
        }
        return result;
    }

    /**
     * Simulates `_create_tracking_values` on `mail.tracking.value`.
     *
     * @param {ModelRecord} initialValue
     * @param {ModelRecord} newValue
     * @param {string} fieldName
     * @param {Object} field
     * @param {string} modelName
     */
    _createTrackingValues(initialValue, newValue, fieldName, field, modelName) {
        let isTracked = true;
        const irField = this.env["ir.model.fields"].find(
            (field) => field.model === modelName && field.name === fieldName
        );
        if (!irField) {
            return;
        }

        const values = { field_id: irField.id };
        switch (irField.ttype) {
            case "char":
            case "datetime":
            case "float":
            case "integer":
            case "text":
                values[`old_value_${irField.ttype}`] = initialValue;
                values[`new_value_${irField.ttype}`] = newValue;
                break;
            case "date":
                values["old_value_datetime"] = initialValue;
                values["new_value_datetime"] = newValue;
                break;
            case "boolean":
                values["old_value_integer"] = initialValue ? 1 : 0;
                values["new_value_integer"] = newValue ? 1 : 0;
                break;
            case "monetary":
                values[`old_value_float`] = initialValue;
                values[`new_value_float`] = newValue;
                break;
            case "selection":
                values["old_value_char"] = initialValue;
                values["new_value_char"] = newValue;
                break;
            case "many2one":
                initialValue = initialValue
                    ? this.env[field.relation].search_read([["id", "=", initialValue]])[0]
                    : initialValue;
                newValue = newValue
                    ? this.env[field.relation].search_read([["id", "=", newValue]])[0]
                    : newValue;
                values["old_value_integer"] = initialValue ? initialValue.id : 0;
                values["new_value_integer"] = newValue ? newValue.id : 0;
                values["old_value_char"] = initialValue ? initialValue.display_name : "";
                values["new_value_char"] = newValue ? newValue.display_name : "";
                break;
            default:
                isTracked = false;
        }
        if (isTracked) {
            return this.create(values);
        }
        return false;
    }

    /**
     * Simulates `_tracking_value_format` on `mail.tracking.value`.
     *
     * @param {ModelRecord[]} trackingValues
     */
    _trackingValueFormat(trackingValues) {
        return trackingValues.map((tracking) => {
            const irField = this.env["ir.model.fields"].find(
                (field) => field.id === tracking.field_id
            );
            return {
                changedField: capitalize(irField.ttype),
                id: tracking.id,
                fieldName: irField.name,
                fieldType: irField.ttype,
                newValue: { value: this._formatDisplayValue(tracking, "new") },
                oldValue: { value: this._formatDisplayValue(tracking, "old") },
            };
        });
    }

    /**
     * Simulates `_format_display_value` on `mail.tracking.value`.
     *
     * @param {ModelRecord} record
     * @param {"new" | "old"} type
     */
    _formatDisplayValue(record, type) {
        const irField = this.env["ir.model.fields"].find((field) => field.id === record.field_id);
        switch (irField.ttype) {
            case "float":
            case "integer":
            case "text":
                return record[`${type}_value_${irField.ttype}`];
            case "datetime":
                if (record[`${type}_value_datetime`]) {
                    const datetime = record[`${type}_value_datetime`];
                    return `${datetime}Z`;
                } else {
                    return record[`${type}_value_datetime`];
                }
            case "date":
                if (record[`${type}_value_datetime`]) {
                    return record[`${type}_value_datetime`];
                } else {
                    return record[`${type}_value_datetime`];
                }
            case "boolean":
                return !!record[`${type}_value_integer`];
            case "monetary":
                return record[`${type}_value_float`];
            default:
                return record[`${type}_value_char`];
        }
    }
}
