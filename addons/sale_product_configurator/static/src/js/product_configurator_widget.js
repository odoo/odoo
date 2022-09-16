/** @odoo-module */
import ProductConfiguratorWidget from "sale.product_configurator";
import { OptionalProductsModal } from "@sale_product_configurator/js/product_configurator_modal";
import {
    selectOrCreateProduct,
    getSelectedVariantValues,
    getNoVariantAttributeValues,
} from "sale.VariantMixin";
import { _t } from "web.core";

/**
 * Extension of the ProductConfiguratorWidget to support product configuration.
 * It opens when a configurable product_template is set.
 * (multiple variants, or custom attributes)
 *
 * The product customization information includes :
 * - is_configurable_product
 * - product_template_attribute_value_ids
 *
 */
ProductConfiguratorWidget.include({
    /**
     * Override of sale.product_configurator Hook
     *
     * @override
     */
    _isConfigurableProduct: function () {
        return this.recordData.is_configurable_product || this._super.apply(this, arguments);
    },

    /**
     * Set restoreProductTemplateId for further backtrack.
     * Saves the optional products in the widget for future application
     * post-line configuration.
     *
     * {OdooEvent ev}
     *    {Array} ev.data.optionalProducts the various selected optional products
     *     with their configuration
     *
     * @override
     * @private
     */
    reset: function (record, ev) {
        if (ev && ev.target === this) {
            this.restoreProductTemplateId = this.recordData.product_template_id;
            this.optionalProducts = (ev.data && ev.data.optionalProducts) || this.optionalProducts;
        }

        this._super.apply(this, arguments);
    },

    /**
     * This method is overridden to check if the product_template_id
     * needs configuration or not:
     *
     * - The product_template has only one "product.product" and is not dynamic
     *   -> Set the product_id on the SO line
     *   -> If the product has optional products, open the configurator in 'options' mode
     *
     * - The product_template is configurable
     *   -> Open the product configurator wizard and initialize it with
     *      the provided product_template_id and its current attribute values
     *
     * @override
     * @private
     */
    _onTemplateChange: function (productTemplateId, dataPointId) {
        var self = this;
        var ctx = {};
        if (this.record && this.recordParams) {
            ctx = this.record.getContext(this.recordParams);
        }

        return this._rpc({
            model: "product.template",
            method: "get_single_product_variant",
            args: [productTemplateId],
            context: ctx,
        }).then(function (result) {
            if (result.product_id && !result.has_optional_products) {
                self.trigger_up("field_changed", {
                    dataPointID: dataPointId,
                    changes: {
                        product_id: { id: result.product_id },
                        product_custom_attribute_value_ids: {
                            operation: "DELETE_ALL",
                        },
                    },
                });
            } else {
                return self._openConfigurator(result, productTemplateId, dataPointId);
            }
            // always returns true for the moment because no other configurator exists.
        });
    },

    /**
     *  When line is configured, apply the options defined earlier.
     *  @override
     *  @private
     */
    _onLineConfigured: function () {
        var self = this;
        this._super.apply(this, arguments);
        var parentList = self.getParent();
        var unselectRow = (parentList.unselectRow || function () {}).bind(parentList); // form view on mobile
        if (self.optionalProducts && self.optionalProducts.length !== 0) {
            self.trigger_up("add_record", {
                context: self._productsToRecords(self.optionalProducts),
                forceEditable: "bottom",
                allowWarning: true,
                onSuccess: function () {
                    // Leave edit mode of one2many list.
                    unselectRow();
                },
            });
        } else if (!self._isConfigurableLine() && self._isConfigurableProduct()) {
            // Leave edit mode of current line if line was configured
            // only through the product configurator.
            unselectRow();
        }
    },

    _openConfigurator: function (result, productTemplateId, dataPointId) {
        if (!result.mode || result.mode === "configurator") {
            this._openProductConfigurator(
                {
                    configuratorMode: result && result.has_optional_products ? "options" : "add",
                    pricelist_id: this._getPricelistId(),
                    product_template_id: productTemplateId,
                },
                dataPointId
            );
            return Promise.resolve(true);
        }
        return Promise.resolve(false);
    },

    /**
     * Opens the product configurator to allow configuring the product template
     * and its various options.
     *
     * The configuratorMode param controls how to open the configurator.
     * - The "add" mode will allow configuring the product template & options.
     * - The "edit" mode will only allow editing the product template's configuration.
     * - The "options" mode is a special case where the product configurator is used as a bridge
     *   between the SO line and the optional products modal. It will hide its window and handle
     *   the communication between those two.
     *
     * When the configuration is canceled (i.e when the product configurator is closed using the
     * "CANCEL" button or the cross on the top right corner of the window),
     * the product_template is reset to its previous value if any.
     *
     * @param {Object} data various "default_" values
     *  {string} data.configuratorMode 'add' or 'edit' or 'options'.
     * @param {string} dataPointId
     *
     * @private
     */
    async _openProductConfigurator(data, dataPointId) {
        this.optionalProducts = undefined;
        const optionalProductsModal = await this._openModal(data);
        // no optional products found for this product, only add the root product
        optionalProductsModal.on("options_empty", null, () =>
            this._addProducts({ mainProduct: this.rootProduct }, dataPointId)
        );

        let confirmed = false;
        optionalProductsModal.on("confirm", null, async () => {
            confirmed = true;
            const [
                mainProduct,
                ...options
            ] = await optionalProductsModal.getAndCreateSelectedProducts();
            this._addProducts({ mainProduct, options }, dataPointId);
        });
        optionalProductsModal.on("closed", null, () => {
            if (confirmed) {
                return;
            }
            if (this.restoreProductTemplateId) {
                // if configurator opened in edit mode.
                this.trigger_up("field_changed", {
                    dataPointID: dataPointId,
                    preventProductIdCheck: true,
                    changes: {
                        product_template_id: this.restoreProductTemplateId.data,
                    },
                });
            } else {
                // if configurator opened to create line:
                // destroy line if configurator closed during configuration process.
                this.trigger_up("field_changed", {
                    dataPointID: dataPointId,
                    changes: {
                        product_template_id: false,
                        product_id: false,
                    },
                });
            }
        });
    },

    async _openModal(data) {
        const {
            product_template_id,
            product_template_attribute_value_ids,
            product_no_variant_attribute_value_ids,
            pricelist_id,
            product_custom_attribute_value_ids,
            quantity,
            configuratorMode,
        } = data;
        // FIXME replace this with an RPC instead of rendering a template and querying it for data
        const $modal = $(
            await this._rpc({
                route: "/sale_product_configurator/configure",
                params: {
                    product_template_id,
                    pricelist_id,
                    add_qty: quantity,
                    product_template_attribute_value_ids,
                    product_no_variant_attribute_value_ids,
                    context: this.getSession().user_context,
                },
            })
        );
        const productSelector = `input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked`;
        const productTemplateId = $modal.find(".product_template_id").val();
        const productId = await selectOrCreateProduct.call(
            this,
            $modal,
            parseInt($modal.find(productSelector).first().val(), 10),
            productTemplateId,
            false
        );
        $modal.find(productSelector).val(productId);
        const variantValues = getSelectedVariantValues($modal);
        const noVariantAttributeValues = getNoVariantAttributeValues($modal);
        this.rootProduct = {
            product_id: productId,
            product_template_id: parseInt(productTemplateId),
            quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
            variant_values: variantValues,
            product_custom_attribute_values: product_custom_attribute_value_ids,
            no_variant_attribute_values: noVariantAttributeValues,
        };
        return new OptionalProductsModal(null, {
            rootProduct: this.rootProduct,
            pricelistId: pricelist_id,
            okButtonText: _t("Confirm"),
            cancelButtonText: _t("Back"),
            title: _t("Configure"),
            context:
                (this.record && this.recordParams && this.record.getContext(this.recordParams)) ||
                {},
            previousModalHeight: this.$el.closest(".modal-content").height(),
            mode: configuratorMode,
        }).open();
    },

    /**
     * Opens the product configurator in "edit" mode.
     * (see '_openProductConfigurator' for more info on the "edit" mode).
     * The requires to retrieve all the needed data from the SO line
     * that are kept in the "recordData" object.
     *
     * @private
     */
    _onEditProductConfiguration: function () {
        if (!this.recordData.is_configurable_product) {
            // if line should be edited by another configurator
            // or simply inline.
            this._super.apply(this, arguments);
            return;
        }
        this.restoreProductTemplateId = this.recordData.product_template_id;
        // If line has been set up through the product_configurator:
        this._openProductConfigurator(
            {
                configuratorMode: "edit",
                product_template_id: this.recordData.product_template_id.data.id,
                pricelist_id: this._getPricelistId(),
                product_template_attribute_value_ids: this._toIdArray(
                    this.recordData.product_template_attribute_value_ids
                ),
                product_no_variant_attribute_value_ids: this._toIdArray(
                    this.recordData.product_no_variant_attribute_value_ids
                ),
                product_custom_attribute_value_ids: this.recordData.product_custom_attribute_value_ids.data.map(
                    (d) => d.data
                ),
                quantity: this.recordData.product_uom_qty,
            },
            this.dataPointID
        );
    },

    _toIdArray(recordData) {
        return recordData ? [...recordData.res_ids] : null;
    },

    /**
     * This will first modify the SO line to update all the information coming from
     * the product configurator using the 'field_changed' event.
     *
     * onSuccess from that first method, it will add the optional products to the SO
     * using the 'add_record' event.
     *
     * Doing both at the same time could lead to unordered product_template/options.
     *
     * @param {Object} products the products to add to the SO line.
     *   {Object} products.mainProduct the product_template configured
     *     with various attribute/custom values
     *   {Array} products.options the various selected optional products
     *     with their configuration
     * @param {string} dataPointId
     *
     * @private
     */
    _addProducts: function (result, dataPointId) {
        this.trigger_up("field_changed", {
            dataPointID: dataPointId,
            preventProductIdCheck: true,
            optionalProducts: result.options,
            changes: this._getMainProductChanges(result.mainProduct),
        });
    },

    /**
     * This will convert the result of the product configurator into
     * "changes" that are understood by the basic_model.js
     *
     * For the product_custom_attribute_value_ids, we need to do a DELETE_ALL
     * command to clean the currently selected values and then a CREATE for every
     * custom value specified in the configurator.
     *
     * For the product_no_variant_attribute_value_ids, we also need to do a DELETE_ALL
     * command to clean the currently selected values and issue a single ADD_M2M containing
     * all the ids of the product_attribute_values.
     *
     * @param {Object} mainProduct
     *
     * @private
     */
    _getMainProductChanges: function (mainProduct) {
        var result = {
            product_id: { id: mainProduct.product_id },
            product_template_id: { id: mainProduct.product_template_id },
            product_uom_qty: mainProduct.quantity,
        };

        var customAttributeValues = mainProduct.product_custom_attribute_values;
        var customValuesCommands = [{ operation: "DELETE_ALL" }];
        if (customAttributeValues && customAttributeValues.length !== 0) {
            _.each(customAttributeValues, function (customValue) {
                // FIXME awa: This could be optimized by adding a "disableDefaultGet" to avoid
                // having multiple default_get calls that are useless since we already
                // have all the default values locally.
                // However, this would mean a lot of changes in basic_model.js to handle
                // those "default_" values and set them on the various fields (text,o2m,m2m,...).
                // -> This is not considered as worth it right now.
                customValuesCommands.push({
                    operation: "CREATE",
                    context: [
                        {
                            default_custom_product_template_attribute_value_id:
                                customValue.custom_product_template_attribute_value_id,
                            default_custom_value: customValue.custom_value,
                        },
                    ],
                });
            });
        }

        result["product_custom_attribute_value_ids"] = {
            operation: "MULTI",
            commands: customValuesCommands,
        };

        var noVariantAttributeValues = mainProduct.no_variant_attribute_values;
        var noVariantCommands = [{ operation: "DELETE_ALL" }];
        if (noVariantAttributeValues && noVariantAttributeValues.length !== 0) {
            var resIds = _.map(noVariantAttributeValues, function (noVariantValue) {
                return { id: parseInt(noVariantValue.value) };
            });

            noVariantCommands.push({
                operation: "ADD_M2M",
                ids: resIds,
            });
        }

        result["product_no_variant_attribute_value_ids"] = {
            operation: "MULTI",
            commands: noVariantCommands,
        };

        return result;
    },

    /**
     * Returns the pricelist_id set on the sale_order form
     *
     * @private
     * @returns {integer} pricelist_id's id
     */
    _getPricelistId: function () {
        return this.record.evalContext.parent.pricelist_id;
    },

    /**
     * Will map the products to appropriate record objects that are
     * ready for the default_get.
     *
     * @param {Array} products The products to transform into records
     *
     * @private
     */
    _productsToRecords: function (products) {
        var records = [];
        _.each(products, function (product) {
            var record = {
                default_product_id: product.product_id,
                default_product_template_id: product.product_template_id,
                default_product_uom_qty: product.quantity,
            };

            if (product.no_variant_attribute_values) {
                var defaultProductNoVariantAttributeValues = [];
                _.each(product.no_variant_attribute_values, function (attributeValue) {
                    defaultProductNoVariantAttributeValues.push([
                        4,
                        parseInt(attributeValue.value),
                    ]);
                });
                record[
                    "default_product_no_variant_attribute_value_ids"
                ] = defaultProductNoVariantAttributeValues;
            }

            if (product.product_custom_attribute_values) {
                var defaultCustomAttributeValues = [];
                _.each(product.product_custom_attribute_values, function (attributeValue) {
                    defaultCustomAttributeValues.push([
                        0,
                        0,
                        {
                            custom_product_template_attribute_value_id:
                                attributeValue.custom_product_template_attribute_value_id,
                            custom_value: attributeValue.custom_value,
                        },
                    ]);
                });
                record["default_product_custom_attribute_value_ids"] = defaultCustomAttributeValues;
            }

            records.push(record);
        });

        return records;
    },
});

export { ProductConfiguratorWidget };
