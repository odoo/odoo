odoo.define('sale.product_configurator', function (require) {
var relationalFields = require('web.relational_fields');
var FieldsRegistry = require('web.field_registry');
var core = require('web.core');
var _t = core._t;

/**
 * The sale.product_configurator widget is a simple widget extending FieldMany2One
 * It allows the development of configuration strategies in other modules through
 * widget extensions.
 *
 *
 * !!! WARNING !!!
 *
 * This widget is only designed for sale_order_line creation/updates.
 * !!! It should only be used on a product_product or product_template field !!!
 */
var ProductConfiguratorWidget = relationalFields.FieldMany2One.extend({
    events: _.extend({}, relationalFields.FieldMany2One.prototype.events, {
        'click .o_edit_product_configuration': '_onEditProductConfiguration'
    }),

     /**
      * @override
      */
    _render: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit' && this.value &&
            (this._isConfigurableProduct() || this._isConfigurableLine())) {
                this._addConfigurationEditButton();
        } else {
            this.$('.o_edit_product_configuration').hide();
        }
    },

    /**
     * If current product is configurable,
     * Show edit button (in Edit Mode) after the product/product_template
     */
    _addConfigurationEditButton: function () {
        var $inputDropdown = this.$('.o_input_dropdown');

        if ($inputDropdown.length !== 0 &&
            this.$('.o_edit_product_configuration').length === 0) {
            var $editConfigurationButton = $('<button>', {
                type: 'button',
                class: 'fa fa-pencil btn btn-secondary o_edit_product_configuration',
                tabindex: '-1',
                draggable: false,
                'aria-label': _t('Edit Configuration'),
                title: _t('Edit Configuration')
            });

            $inputDropdown.after($editConfigurationButton);
        }
    },

    /**
     * Hook to override with _onEditProductConfiguration
     * to know if edit pencil button has to be put next to the field
     *
     * @private
     */
    _isConfigurableProduct: function () {
        return false;
    },

    /**
     * Hook to override with _onEditProductConfiguration
     * to know if edit pencil button has to be put next to the field
     *
     * @private
     */
    _isConfigurableLine: function () {
        return false;
    },

    /**
     * Override catching changes on product_id or product_template_id.
     * Calls _onTemplateChange in case of product_template change.
     * Calls _onProductChange in case of product change.
     * Shouldn't be overridden by product configurators
     * or only to setup some data for further computation
     * before calling super.
     *
     * @override
     * @param {OdooEvent} ev
     *   {boolean} ev.data.preventProductIdCheck prevent the product configurator widget
     *     from looping forever when it needs to change the 'product_template_id'
     *
     * @private
     */
    _onFieldChanged: function (ev) {
        var self = this;

        this._super.apply(this, arguments);

        if (ev.data.changes && !ev.data.preventProductIdCheck && ev.data.changes.product_template_id) {
            self._onTemplateChange(ev.data.changes.product_template_id.id, ev.data.dataPointID);
        } else if (ev.data.changes && ev.data.changes.product_id) {
            self._onProductChange(ev.data.changes.product_id.id, ev.data.dataPointID);
        }
    },

    /**
     * Hook for product_template based configurators
     * (product configurator, matrix, ...).
     *
     * @param {integer} productTemplateId
     * @param {String} dataPointID
     *
     * @private
     */
    _onTemplateChange: function (productTemplateId, dataPointId) {
        return Promise.resolve(false);
    },

    /**
     * Hook for product_product based configurators
     * (event, rental, ...).
     * Should return
     *    true if product has been configured through wizard or
     *        the result of the super call for other wizard extensions
     *    false if the product wasn't configurable through the wizard
     *
     * @param {integer} productId
     * @param {String} dataPointID
     * @returns {Promise<Boolean>} stopPropagation true if a suitable configurator has been found.
     *
     * @private
     */
    _onProductChange: function (productId, dataPointId) {
        return Promise.resolve(false);
    },

    /**
     * Hook for editing a configured line.
     * The button triggering this function is only shown in Edit mode,
     * when _isConfigurableProduct is True.
     *
     * @private
     */
    _onEditProductConfiguration: function () {

    },

    /**
     * Utilities for recordData conversion
     */

    /**
     * Will convert the values contained in the recordData parameter to
     * a list of '4' operations that can be passed as a 'default_' parameter.
     *
     * @param {Object} recordData
     *
     * @private
     */
    _convertFromMany2Many: function (recordData) {
        if (recordData) {
            var convertedValues = [];
            _.each(recordData.res_ids, function (resId) {
                convertedValues.push([4, parseInt(resId)]);
            });

            return convertedValues;
        }

        return null;
    },

    /**
     * Will convert the values contained in the recordData parameter to
     * a list of '0' or '4' operations (based on wether the record is already persisted or not)
     * that can be passed as a 'default_' parameter.
     *
     * @param {Object} recordData
     *
     * @private
     */
    _convertFromOne2Many: function (recordData) {
        if (recordData) {
            var convertedValues = [];
            _.each(recordData.res_ids, function (resId) {
                if (isNaN(resId)) {
                    _.each(recordData.data, function (record) {
                        if (record.ref === resId) {
                            convertedValues.push([0, 0, {
                                attribute_value_id: record.data.attribute_value_id.data.id,
                                custom_value: record.data.custom_value
                            }]);
                        }
                    });
                } else {
                    convertedValues.push([4, resId]);
                }
            });

            return convertedValues;
        }

        return null;
    }
});

FieldsRegistry.add('product_configurator', ProductConfiguratorWidget);

return ProductConfiguratorWidget;

});
