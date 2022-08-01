/** @odoo-module **/

import { registerModel } from '@mail/model/model_core';
import { attr, one } from '@mail/model/model_field';

import { format } from 'web.field_utils';
import { session } from '@web/session';
import { registry } from '@web/core/registry';
import { deserializeDateTime } from '@web/core/l10n/dates';

const formatters = registry.category("formatters");

registerModel({
    name: 'TrackingValueItem',
    identifyingFields: [['trackingValueAsNewValue','trackingValueAsOldValue']],
    recordMethods: {
        /**
         * @private
         * @returns {string}
         */
        _computeFormattedValue() {
            /**
             * Maps tracked field type to a JS formatter. Tracking values are
             * not always stored in the same field type as their origin type.
             * Field types that are not listed here are not supported by
             * tracking in Python. Also see `create_tracking_values` in Python.
             */
            switch (this.fieldType) {
                case 'boolean':
                    return this.value ? this.env._t("Yes") : this.env._t("No");
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
                    return format.char(this.value);
                case 'date':
                    if (this.value) {
                        return format.date(moment.utc(this.value));
                    }
                    return format.date(this.value);
                case 'datetime': {
                    const value = this.value ? deserializeDateTime(this.value) : this.value;
                    return formatters.get("datetime")(value, { timezone: true });
                }
                case 'float':
                    return format.float(this.value);
                case 'integer':
                    return format.integer(this.value);
                case 'text':
                    return format.text(this.value);
                case 'monetary':
                    return format.monetary(this.value, undefined, {
                        currency: this.currencyId
                            ? session.currencies[this.currencyId]
                            : undefined,
                        forceString: true,
                    });
                default :
                    return this.value;
            }
        },
        /**
         * @private
         * @returns {string}
         */
        _computeFormattedValueOrNone() {
            return this.formattedValue || this.env._t("None");
        },
    },
    fields: {
        /**
         * Used when the currency changes as the tracking value. This only makes sense for field of type monetary.
         */
        currencyId: attr(),
        /**
         * Indicates the type of the tracking value item.
         * The supported types are: boolean, char, many2one, selection, date, datetime, float, integer, text, monetary.
         */
        fieldType: attr(),
        formattedValue: attr({
            compute: '_computeFormattedValue',
        }),
        formattedValueOrNone: attr({
            compute: '_computeFormattedValueOrNone',
        }),
        trackingValueAsNewValue: one('TrackingValue', {
            inverse: 'newValue',
            readonly: true,
        }),
        trackingValueAsOldValue: one('TrackingValue', {
            inverse: 'oldValue',
            readonly: true,
        }),
        /**
         * The original value of the tracking value item.
         */
        value: attr(),
}});
