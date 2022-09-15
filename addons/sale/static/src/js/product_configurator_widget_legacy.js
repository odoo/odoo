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
        'click .o_edit_product_configuration': '_onEditConfiguration'
    }),

     /**
      * @override
      */
    _render: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit' && this.value &&
        (this._isConfigurableProduct() || this._isConfigurableLine())) {
            this._addProductLinkButton();
            this._addConfigurationEditButton();
        } else if (this.mode === 'edit' && this.value) {
            this._addProductLinkButton();
            this.$('.o_edit_product_configuration').hide();
        } else {
            this.$('.o_external_button').hide();
            this.$('.o_edit_product_configuration').hide();
        }
    },

    /**
     * Add button linking to product_id/product_template_id form.
     */
    _addProductLinkButton: function () {
        if (this.$('.o_external_button').length === 0) {
            var $productLinkButton = $('<button>', {
                type: 'button',
                class: 'fa fa-external-link btn btn-secondary o_external_button',
                tabindex: '-1',
                draggable: false,
                'aria-label': _t('External Link'),
                title: _t('External Link')
            });

            var $inputDropdown = this.$('.o_input_dropdown');
            $inputDropdown.after($productLinkButton);
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
     * @param {boolean} ev.data.preventProductIdCheck prevent the product configurator widget
     *     from looping forever when it needs to change the 'product_template_id'
     *
     * @private
     */
    reset: async function (record, ev) {
        await this._super(...arguments);
        if (ev && ev.target === this) {
            if (ev.data.changes && !ev.data.preventProductIdCheck && ev.data.changes.product_template_id) {
                this._onTemplateChange(record.data.product_template_id.data.id, ev.data.dataPointID);
            } else if (ev.data.changes && ev.data.changes.product_id) {
                this._onProductChange(record.data.product_id.data && record.data.product_id.data.id, ev.data.dataPointID).then(wizardOpened => {
                    if (!wizardOpened) {
                        this._onLineConfigured();
                    }
                });
            }
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
     * Hook for configurator happening after line has been set
     * (options, ...).
     * Allows sale_product_configurator module to apply its options
     * after line configuration has been done.
     *
     * @private
     */
    _onLineConfigured: function () {

    },

    /**
     * Triggered on click of the configuration button.
     * It is only shown in Edit mode,
     * when _isConfigurableProduct or _isConfigurableLine is True.
     *
     * After reflexion, when a line was configured through two wizards,
     * only the line configuration will open.
     *
     * Two hooks are available depending on configurator category:
     * _onEditLineConfiguration : line configurators
     * _onEditProductConfiguration : product configurators
     *
     * @private
     */
    _onEditConfiguration: function () {
        if (this._isConfigurableLine()) {
            this._onEditLineConfiguration();
        } else if (this._isConfigurableProduct()) {
            this._onEditProductConfiguration();
        }
    },

    /**
     * Hook for line configurators (rental, event)
     * on line edition (pencil icon inside product field)
     */
    _onEditLineConfiguration: function () {

    },

    /**
     * Hook for product configurators (matrix, product)
     * on line edition (pencil icon inside product field)
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
                                custom_product_template_attribute_value_id: record.data.custom_product_template_attribute_value_id.data.id,
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
