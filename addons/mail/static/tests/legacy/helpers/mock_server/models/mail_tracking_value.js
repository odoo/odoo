/** @odoo-module alias=@mail/../tests/helpers/mock_server/models/mail_tracking_value default=false */

import { patch } from "@web/core/utils/patch";
import { capitalize } from "@web/core/utils/strings";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, {
    /**
     * @override
     */
    init(data, options) {
        super.init(data, options);
        // creation of the ir.model.fields records, required for tracked fields
        for (const modelName in this.models) {
            const fieldNamesToFields = this.models[modelName].fields;
            for (const [fname, field] of Object.entries(fieldNamesToFields)) {
                if (fieldNamesToFields[fname].tracking) {
                    this.mockCreate("ir.model.fields", {
                        model: modelName,
                        name: fname,
                        ttype: field.type,
                    });
                }
            }
        }
    },
    /**
     * @override
     */
    mockWrite(model) {
        const initialTrackedFieldValuesByRecordId = this._mockMailThread_TrackPrepare(model);
        const mockWriteResult = super.mockWrite(...arguments);
        if (initialTrackedFieldValuesByRecordId) {
            this._mockMailThread_TrackFinalize(model, initialTrackedFieldValuesByRecordId);
        }
        return mockWriteResult;
    },
    /**
     * Simulates `_create_tracking_values` on `mail.tracking.value`
     */
    _mockMailTrackingValue_CreateTrackingValues(
        initialValue,
        newValue,
        fieldName,
        field,
        modelName
    ) {
        let isTracked = true;
        const irField = this.models["ir.model.fields"].records.find(
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
                    ? this.pyEnv[field.relation].search_read([["id", "=", initialValue]])[0]
                    : initialValue;
                newValue = newValue
                    ? this.pyEnv[field.relation].search_read([["id", "=", newValue]])[0]
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
            return this.pyEnv["mail.tracking.value"].create(values);
        }
        return false;
    },
    /**
     * Simulates `_tracking_value_format` on `mail.tracking.value`
     */
    _mockMailTrackingValue_TrackingValueFormat(tracking_value_ids) {
        const trackingValues = tracking_value_ids.map((tracking) => {
            const irField = this.models["ir.model.fields"].records.find(
                (field) => field.id === tracking.field_id
            );
            return {
                changedField: capitalize(irField.ttype),
                id: tracking.id,
                fieldName: irField.name,
                fieldType: irField.ttype,
                newValue: {
                    value: this._mockMailTrackingValue_FormatDisplayValue(tracking, "new"),
                },
                oldValue: {
                    value: this._mockMailTrackingValue_FormatDisplayValue(tracking, "old"),
                },
            };
        });
        return trackingValues;
    },
    /**
     * Simulates `_format_display_value` on `mail.tracking.value`
     */
    _mockMailTrackingValue_FormatDisplayValue(record, type) {
        const irField = this.models["ir.model.fields"].records.find(
            (field) => field.id === record.field_id
        );
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
    },
});
