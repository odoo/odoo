/** @odoo-module **/

import { registerNewModel } from '@mail/model/model_core';
import { attr, many2one } from '@mail/model/model_field';

import { format } from 'web.field_utils';

function factory(dependencies) {

    class MessageTrackingValue extends dependencies['mail.model'] {

        //----------------------------------------------------------------------
        // Public
        //----------------------------------------------------------------------
        /**
         * @static
         * @param {Object} data
         * @return {Object}
         */
         static convertData(data) {
            const data2 = {};
            if ('id' in data) {
                data2.id = data.id;
            }
            if ('changed_field' in data) {
                data2.changedField = data.changed_field;
            }
            if ('currency_id' in data) {
                data2.currencyId = data.currency_id;
            }
            if ('field_type' in data) {
                data2.fieldType = data.field_type;
            }
            if ('new_value' in data) {
                data2.newValue = data.new_value;
            }
            if ('old_value' in data) {
                data2.oldValue = data.old_value;
            }
            return data2;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------

        /**
         * @override
         */
         static _createRecordLocalId(data) {
            return `${this.modelName}_${data.id}`;
        }

        /**
         * @private
         * @returns {string}
         */
         _computeChangedField() {
            return _.str.sprintf(this.env._t("%s:"), this.changedField);
        }

        /**
         * @private
         * @param {string} fieldType
         * @param {string|boolean|float|number|integer|Array|Object} value
         * @returns {string}
         */
        static _formatMessageTrackingValue(fieldType, value) {
            /**
             * Maps tracked field type to a JS formatter. Tracking values are
             * not always stored in the same field type as their origin type.
             * Field types that are not listed here are not supported by
             * tracking in Python. Also see `create_tracking_values` in Python.
             */
            switch (fieldType) {
                case 'boolean':
                    return format.boolean(value, undefined, { forceString: true });
                /**
                 * many2one formatter exists but is expecting id/name_get or data
                 * object but only the target record name is known in this context.
                 *
                 * Selection formatter exists but requires knowing all
                 * possibilities and they are not given in this context.
                 */
                case 'char':
                case 'many2one':
                case 'selection':
                    return format.char(value);
                case 'date':
                    if (value) {
                        value = moment.utc(value);
                    }
                    return format.date(value);
                case 'datetime':
                    if (value) {
                        value = moment.utc(value);
                    }
                    return format.datetime(value);
                case 'float':
                    return format.float(value);
                case 'integer':
                    return format.integer(value);
                case 'text':
                    return format.text(value);
                default : 
                    return undefined;
            }
        }

        /**
         * @private
         * @returns {string}
         */
        _computeOldValue() {
            if (this.fieldType == 'monetary') {
                return format.monetary(this.oldValue, undefined, {
                    currency: this.currencyId
                        ? this.env.session.currencies[this.currencyId]
                        : undefined,
                    forceString: true,
                });
            }
            return MessageTrackingValue._formatMessageTrackingValue(this.fieldType, this.oldValue);
        }

        /**
         * @private
         * @returns {string}
         */
         _computeNewValue() {
             if (this.fieldType == 'monetary') {
                return format.monetary(this.newValue, undefined, {
                    currency: this.currencyId
                        ? this.env.session.currencies[this.currencyId]
                        : undefined,
                    forceString: true,
                });
            }
            return MessageTrackingValue._formatMessageTrackingValue(this.fieldType, this.newValue);
        }
    }

    MessageTrackingValue.fields = {
        /**
         * The formatted string of the chanegd field name, such as "Status", "Date", etc.
         */
        changedFieldAsString: attr({
            compute: '_computeChangedField',
            dependencies: [
                'changedField',
            ],
        }),
        changedField: attr(),
        /**
         * Used when the currency changes as the tracking value.
         */
        currencyId: attr(),
        /**
         * Indicate the type of the tracking value, such as float, integer, date.
         */
        fieldType: attr(),
        id: attr({
            required: true,
        }),
        message: many2one('mail.message', {
            inverse: 'trackingValues',
        }),
        newValueAsString: attr({
            compute: '_computeNewValue',
            dependencies: [
                'currencyId',
                'fieldType',
                'newValue',
            ],
        }),
        newValue: attr(),
        oldValueAsString: attr({
            compute: '_computeOldValue',
            dependencies: [
                'currencyId',
                'fieldType',
                'oldValue',
            ],
        }),
        oldValue: attr(),
    };

    MessageTrackingValue.modelName = 'mail.message_tracking_value';

    return MessageTrackingValue;
}

registerNewModel('mail.message_tracking_value', factory);
