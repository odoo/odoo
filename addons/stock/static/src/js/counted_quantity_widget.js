/** @odoo-module alias=stock.counted_quantity_widget **/

import BasicFields from 'web.basic_fields';
import fieldRegistry from 'web.field_registry';

const CountedQuantityWidgetField = BasicFields.FieldFloat.extend({
    supportedFieldTypes: ['float'],

     _renderReadonly: function () {
        if (this.recordData.inventory_quantity_set) {
            this.el.textContent = this._formatValue(this.recordData.inventory_quantity);
        } else {
            this.el.textContent = "";
        }
    },

    _onChange: function () {
        if (!this.recordData.inventory_quantity_set) {
            this.recordData.inventory_quantity_set = true;
        }
        this._super.apply(this);
    },

    _isSameValue: function(value) {
        // We want to trigger the update of the view when inserting 0
        if (value == 0) {
            return false;
        }
        return this._super(...arguments);
    }

});

fieldRegistry.add('counted_quantity_widget', CountedQuantityWidgetField);

export default CountedQuantityWidgetField;
