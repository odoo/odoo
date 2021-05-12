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
            const messageTrackingValue = {
                id: data.id,
            };
            if ('changed_field' in data) {
                messageTrackingValue.changedFieldOriginal = data.changed_field;
            }
            if ('currency_id' in data) {
                messageTrackingValue.currencyId = data.currency_id;
            }
            if ('field_type' in data) {
                messageTrackingValue.fieldType = data.field_type;
            }
            if ('new_value' in data) {
                messageTrackingValue.newValueOriginal = data.new_value;
            }
            if ('old_value' in data) {
                messageTrackingValue.oldValueOriginal = data.old_value;
            }

            return messageTrackingValue;
        }

        //----------------------------------------------------------------------
        // Private
        //----------------------------------------------------------------------
        
        /**
         * @private
         * @returns {string}
         */
         _computeChangedField() {
            return _.str.sprintf(this.env._t("%s:"), this.changedFieldOriginal);
        }

        /**
         * @private
         * @returns {string}
         */
        _formatValue(fieldType, value) {
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
                case 'monetary':
                    return format.monetary(value, undefined, {
                        currency: this.currencyId
                            ? this.env.session.currencies[this.currencyId]
                            : undefined,
                        forceString: true,
                    });
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
            /**
             * Maps tracked field type to a JS formatter. Tracking values are
             * not always stored in the same field type as their origin type.
             * Field types that are not listed here are not supported by
             * tracking in Python. Also see `create_tracking_values` in Python.
             */
            return this._formatValue(this.fieldType, this.oldValueOriginal)
        }

        /**
         * @private
         * @returns {string}
         */
         _computeNewValue() {
            /**
             * Maps tracked field type to a JS formatter. Tracking values are
             * not always stored in the same field type as their origin type.
             * Field types that are not listed here are not supported by
             * tracking in Python. Also see `create_tracking_values` in Python.
             */
            return this._formatValue(this.fieldType, this.newValueOriginal)
        }
    }

    MessageTrackingValue.fields = {

        changedField: attr({
            compute: '_computeChangedField',
            dependencies: [
                'changedFieldOriginal',
            ],
        }),
        changedFieldOriginal: attr(),
        currencyId: attr(),
        fieldType: attr(),
        id: attr({
            required: true,
        }),
        message: many2one('mail.message', {
            inverse: 'trackingValues',
        }),
        newValue: attr({
            compute: '_computeNewValue',
            dependencies: [
                'fieldType',
                'newValueOriginal',
            ],
        }),
        newValueOriginal: attr(),
        oldValue: attr({
            compute: '_computeOldValue',
            dependencies: [
                'fieldType',
                'oldValueOriginal',
            ],
        }),
        oldValueOriginal: attr()
    };

    MessageTrackingValue.modelName = 'mail.message_tracking_value';

    return MessageTrackingValue;
}

registerNewModel('mail.message_tracking_value', factory);
    