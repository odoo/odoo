odoo.define('sale_product_matrix.product_configurator', function (require) {
var ProductConfiguratorWidget = require('sale_product_configurator.product_configurator');

/**
 * Extension of the ProductConfiguratorWidget to support product configuration
 * as variant batches to add to the SO..
 * It opens when a configurable product_template is set
 * (multiple variants, or custom attributes)
 * and its configuration mode is matrix.
 *
 */
ProductConfiguratorWidget.include({

    /**
     * @override
     */
     _openConfigurator: function (result, productTemplateId, dataPointId) {
        var self = this;
        var mode = result.mode;
        this._super.apply(this, arguments).then(function (configuratorOpened) {
            if (!configuratorOpened && mode === 'matrix') {
                self._openGridConfigurator(productTemplateId, dataPointId);
                return Promise.resolve(true);
            }
            return Promise.resolve(configuratorOpened);
        });
    },

    _openGridConfigurator: function (productTemplateId, dataPointId, edit) {
        var attribs = edit ? this._getPTAVS() : [];
        this.trigger_up('open_matrix', {
            product_template_id: productTemplateId,
            model: 'sale.order',
            dataPointId: dataPointId,
            edit: edit,
            editedCellAttributes: attribs,
        });
    },

    _onEditProductConfiguration: function () {
        if (!this.recordData.is_configurable_product) {
            // if line should be edited by another configurator
            // or simply inline.
            this._super.apply(this, arguments);
            return;
        }
        var self = this;
        var productTemplateId = this.recordData.product_template_id.data.id;
        this._rpc({
            model: 'product.template',
            method: 'read',
            args: [productTemplateId, ['product_add_mode']],
        }).then(function (result) {
            if (result && result[0].product_add_mode === 'matrix') {
                self._openGridConfigurator(productTemplateId, self.dataPointID, true);
            } else {
                // Call super only if product_add_mode different than matrix
                // to avoid product configurator opening (which is the default case).
                self._openProductConfigurator({
                        configuratorMode: 'edit',
                        default_product_template_id: self.recordData.product_template_id.data.id,
                        default_pricelist_id: self._getPricelistId(),
                        default_product_template_attribute_value_ids: self._convertFromMany2Many(
                            self.recordData.product_template_attribute_value_ids
                        ),
                        default_product_no_variant_attribute_value_ids: self._convertFromMany2Many(
                            self.recordData.product_no_variant_attribute_value_ids
                        ),
                        default_product_custom_attribute_value_ids: self._convertFromOne2Many(
                            self.recordData.product_custom_attribute_value_ids
                        ),
                        default_quantity: self.recordData.product_uom_qty
                    },
                    self.dataPointID
                );
            }
        });
    },

    /**
     * Returns the list of attribute ids (product.template.attribute.value)
     * from the current SOLine.
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

});
