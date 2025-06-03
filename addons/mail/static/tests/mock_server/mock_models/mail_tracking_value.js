import { getKwArgs, models } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { capitalize } from "@web/core/utils/strings";

patch(models.ServerModel.prototype, {
    /**
     * @override
     * @type {typeof models.Model["prototype"]["write"]}
     */
    write() {
        /** @type {import("mock_models").MailThread} */
        const MailThread = this.env["mail.thread"];

        const initialTrackedFieldValuesByRecordId = MailThread._track_prepare.call(this);
        const result = super.write(...arguments);
        if (initialTrackedFieldValuesByRecordId) {
            MailThread._track_finalize.call(this, initialTrackedFieldValuesByRecordId);
        }
        return result;
    },
});
/**
 * @typedef {import("@web/../tests/web_test_helpers").ModelRecord} ModelRecord
 */

export class MailTrackingValue extends models.ServerModel {
    _name = "mail.tracking.value";

    /**
     * @param {ModelRecord} initial_value
     * @param {ModelRecord} new_value
     * @param {string} col_name
     * @param {Object} col_info
     * @param {models.ServerModel} record
     */
    _create_tracking_values(initial_value, new_value, col_name, col_info, record) {
        const kwargs = getKwArgs(
            arguments,
            "initial_value",
            "new_value",
            "col_name",
            "col_info",
            "record"
        );
        initial_value = kwargs.initial_value;
        new_value = kwargs.new_value;
        col_name = kwargs.col_name;
        col_info = kwargs.col_info;
        record = kwargs.record;

        /** @type {import("mock_models").IrModelFields} */
        const IrModelFields = this.env["ir.model.fields"];

        let isTracked = true;
        const irField = IrModelFields.find(
            (field) => field.model === record._name && field.name === col_name
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
                values[`old_value_${irField.ttype}`] = initial_value;
                values[`new_value_${irField.ttype}`] = new_value;
                break;
            case "date":
                values["old_value_datetime"] = initial_value;
                values["new_value_datetime"] = new_value;
                break;
            case "boolean":
                values["old_value_integer"] = initial_value ? 1 : 0;
                values["new_value_integer"] = new_value ? 1 : 0;
                break;
            case "monetary": {
                values["old_value_float"] = initial_value;
                values["new_value_float"] = new_value;
                let currencyField = col_info.currency_field;
                // see get_currency_field in python fields
                if (!currencyField && "currency_id" in record._fields) {
                    currencyField = "currency_id";
                }
                values[`currency_id`] = record[0][currencyField];
                break;
            }
            case "selection":
                values["old_value_char"] = initial_value;
                values["new_value_char"] = new_value;
                break;
            case "many2one":
                initial_value = initial_value
                    ? this.env[col_info.relation].search_read([["id", "=", initial_value]])[0]
                    : initial_value;
                new_value = new_value
                    ? this.env[col_info.relation].search_read([["id", "=", new_value]])[0]
                    : new_value;
                values["old_value_integer"] = initial_value ? initial_value.id : 0;
                values["new_value_integer"] = new_value ? new_value.id : 0;
                values["old_value_char"] = initial_value ? initial_value.display_name : "";
                values["new_value_char"] = new_value ? new_value.display_name : "";
                break;
            default:
                isTracked = false;
        }
        if (isTracked) {
            return this.create(values);
        }
        return false;
    }

    /** @param {ModelRecord[]} trackingValues */
    _tracking_value_format(trackingValues) {
        /** @type {import("mock_models").IrModelFields} */
        const IrModelFields = this.env["ir.model.fields"];

        return trackingValues.map((tracking) => {
            const irField = IrModelFields.find((field) => field.id === tracking.field_id);
            return {
                changedField: capitalize(irField.ttype),
                id: tracking.id,
                fieldName: irField.name,
                fieldType: irField.ttype,
                newValue: {
                    currencyId: tracking.currency_id,
                    floatPrecision: this.env[irField.model]._fields[irField.name].digits,
                    value: this._format_display_value(tracking, "new"),
                },
                oldValue: {
                    currencyId: tracking.currency_id,
                    floatPrecision: this.env[irField.model]._fields[irField.name].digits,
                    value: this._format_display_value(tracking, "old"),
                },
            };
        });
    }

    /**
     * @param {ModelRecord} record
     * @param {"new" | "old"} field_type
     */
    _format_display_value(record, field_type) {
        const kwargs = getKwArgs(arguments, "record", "field_type");
        record = kwargs.record;
        field_type = kwargs.field_type;

        /** @type {import("mock_models").IrModelFields} */
        const IrModelFields = this.env["ir.model.fields"];

        const irField = IrModelFields.find((field) => field.id === record.field_id);
        switch (irField.ttype) {
            case "float":
            case "integer":
            case "text":
                return record[`${field_type}_value_${irField.ttype}`];
            case "datetime":
                if (record[`${field_type}_value_datetime`]) {
                    const datetime = record[`${field_type}_value_datetime`];
                    return `${datetime}Z`;
                } else {
                    return record[`${field_type}_value_datetime`];
                }
            case "date":
                if (record[`${field_type}_value_datetime`]) {
                    return record[`${field_type}_value_datetime`];
                } else {
                    return record[`${field_type}_value_datetime`];
                }
            case "boolean":
                return !!record[`${field_type}_value_integer`];
            case "monetary":
                return record[`${field_type}_value_float`];
            default:
                return record[`${field_type}_value_char`];
        }
    }
}
