/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { MockServer } from "@web/../tests/helpers/mock_server";

patch(MockServer.prototype, 'mail/models/mail_tracking_value', {
    /**
     * @override
     */
    init(data, options) {
        this._super(data, options);
        if (this.currentPartnerId && this.models && 'res.partner' in this.models) {
            this.currentPartner = this.getRecords('res.partner', [['id', '=', this.currentPartnerId]])[0];
        }
        // creation of the ir.model.fields records, required for tracked fields
        for (const modelName in this.models) {
          const fieldNamesToFields = this.models[modelName].fields;
            for (const fname in fieldNamesToFields) {
              if (fieldNamesToFields[fname].tracking) {
                  this.mockCreate('ir.model.fields', { model: modelName, name: fname });
                }
            }
        }
    },
    /**
     * @override
     */
    mockWrite(model) {
        const initialTrackedFieldValuesByRecordId = this._mockMailThread_TrackPrepare(model);
        const mockWriteResult = this._super(...arguments);
        if (initialTrackedFieldValuesByRecordId) {
            this._mockMailThread_TrackFinalize(model, initialTrackedFieldValuesByRecordId);
        }
        return mockWriteResult;
    },
    /**
     * Simulates `create_tracking_values` on `mail.tracking.value`
     */
    _mockMailTrackingValue_CreateTrackingValues(initialValue, newValue, fieldName, field, modelName) {
        let isTracked = true;
        const irField = this.models['ir.model.fields'].records.find(field => field.model === modelName && field.name === fieldName);

        if (!irField) {
            return;
        }

        const values = { field: irField['id'], field_desc: field['string'], field_type: field['type'] };
        switch (values.field_type) {
            case 'char':
            case 'datetime':
            case 'float':
            case 'integer':
            case 'monetary':
            case 'text':
                values[`old_value_${values.field_type}`] = initialValue;
                values[`new_value_${values.field_type}`] = newValue;
                break;
            case 'date':
                values['old_value_datetime'] = initialValue;
                values['new_value_datetime'] = newValue;
                break;
            case 'boolean':
                values['old_value_integer'] = initialValue ? 1 : 0;
                values['new_value_integer'] = newValue ? 1 : 0;
                break;
            case 'selection':
                values['old_value_char'] = initialValue;
                values['new_value_char'] = newValue;
                break;
            case 'many2one':
                initialValue = initialValue ? this.pyEnv[field.relation].searchRead([['id', '=', initialValue]])[0] : initialValue;
                newValue = newValue ? this.pyEnv[field.relation].searchRead([['id', '=', newValue]])[0] : newValue;
                values['old_value_integer'] = initialValue ? initialValue.id : 0;
                values['new_value_integer'] = newValue ? newValue.id : 0;
                values['old_value_char'] = initialValue ? initialValue.display_name : '';
                values['new_value_char'] = newValue ? newValue.display_name : '';
                break;
            default:
                isTracked = false;
        }
        if (isTracked) {
            return this.pyEnv['mail.tracking.value'].create(values);
        }
        return false;
    },
    /**
     * Simulates `_tracking_value_format` on `mail.tracking.value`
     */
    _mockMailTrackingValue_TrackingValueFormat(tracking_value_ids) {
        const trackingValues = tracking_value_ids.map(tracking => ({
            changedField: tracking.field_desc,
            id: tracking.id,
            newValue: {
                fieldType: tracking.field_type,
                value: this._mockMailTrackingValue_GetDisplayValue(tracking, 'new')
            },
            oldValue: {
                fieldType: tracking.field_type,
                value: this._mockMailTrackingValue_GetDisplayValue(tracking, 'old')
            },
        }));
        return trackingValues;
    },
    /**
     * Simulates `_get_display_value` on `mail.tracking.value`
     */
    _mockMailTrackingValue_GetDisplayValue(record, type) {
        switch (record.field_type) {
            case 'float':
            case 'integer':
            case 'monetary':
            case 'text':
                return record[`${type}_value_${record.field_type}`];
            case 'datetime':
                if (record[`${type}_value_datetime`]) {
                    const datetime = record[`${type}_value_datetime`];
                    return `${datetime}Z`;
                } else {
                    return record[`${type}_value_datetime`];
                }
            case 'date':
                if (record[`${type}_value_datetime`]) {
                    return record[`${type}_value_datetime`];
                } else {
                    return record[`${type}_value_datetime`];
                }
            case 'boolean':
                return !!record[`${type}_value_integer`];
            default:
                return record[`${type}_value_char`];
        }
    },
});
