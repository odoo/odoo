odoo.define('purchase.product_matrix_configurator', function (require) {

var relationalFields = require('web.relational_fields');
var FieldsRegistry = require('web.field_registry');
var core = require('web.core');
var _t = core._t;

/**
 * The purchase.product_matrix_configurator widget is a widget extending FieldMany2One
 * It triggers the opening of the matrix edition when the product has multiple variants.
 *
 *
 * !!! WARNING !!!
 *
 * This widget is only designed for Purchase Order Lines.
 * !!! It should only be used on a product_template field !!!
 */
var MatrixConfiguratorWidget = relationalFields.FieldMany2One.extend({
    events: _.extend({}, relationalFields.FieldMany2One.prototype.events, {
        'click .o_edit_product_configuration': '_onEditProductConfiguration'
    }),

    /**
     * @override
     */
    _render: function () {
       this._super.apply(this, arguments);
       if (this.mode === 'edit' && this.value &&
       (this._isConfigurableProduct())) {
           this._addProductLinkButton();
           this._addConfigurationEditButton();
       } else if (this.mode === 'edit' && this.value) {
           this._addProductLinkButton();
       } else {
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
        return this.recordData.is_configurable_product;
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
     * @private
     */
    _onFieldChanged: function (ev) {
        var self = this;

        this._super.apply(this, arguments);

        if (ev.data.changes && ev.data.changes.product_template_id) {
            self._onTemplateChange(ev.data.changes.product_template_id.id, ev.data.dataPointID);
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
        var self = this;
        this._rpc({
            model: 'product.template',
            method: 'get_single_product_variant',
            args: [
                productTemplateId
            ]
        }).then(function (result) {
            if (result.product_id) {
                self.trigger_up('field_changed', {
                    dataPointID: dataPointId,
                    changes: {
                        product_id: {id: result.product_id},
                    },
                });
            } else {
                self._openMatrix(productTemplateId, dataPointId, false);
            }
        });
    },

    /**
     * Hook for editing a configured line.
     * The button triggering this function is only shown in Edit mode,
     * when _isConfigurableProduct is True.
     *
     * @private
     */
    _onEditProductConfiguration: function () {
        if (this.recordData.is_configurable_product) {
            this._openMatrix(this.recordData.product_template_id.data.id, this.dataPointID, true);
        }
    },

    _openMatrix: function (productTemplateId, dataPointId, edit) {
        var attribs = edit ? this._getPTAVS() : [];
        this.trigger_up('open_matrix', {
            product_template_id: productTemplateId,
            model: 'purchase.order',
            dataPointId: dataPointId,
            edit: edit,
            editedCellAttributes: attribs,
            // used to focus the cell representing the line on which the pencil was clicked.
        });
    },

    /**
     * Returns the list of attribute ids (product.template.attribute.value)
     * from the current POLine.
    */
    _getPTAVS: function () {
        var PTAVSIDS = [];
        _.each(this.recordData.product_no_variant_attribute_value_ids.res_ids, function (id) {
            PTAVSIDS.push(id);
        });
        _.each(this.recordData.product_template_attribute_value_ids.res_ids, function (id) {
            PTAVSIDS.push(id);
        });
        return PTAVSIDS.sort(function (a, b) {return a - b;});
    }
});

FieldsRegistry.add('matrix_configurator', MatrixConfiguratorWidget);

return MatrixConfiguratorWidget;

});
