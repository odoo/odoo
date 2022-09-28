/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { OptionalProductsModal } from "@sale_product_configurator/js/product_configurator_modal";
import {
    selectOrCreateProduct,
    getSelectedVariantValues,
    getNoVariantAttributeValues,
} from "sale.VariantMixin";


patch(SaleOrderLineProductField.prototype, 'sale_product_configurator', {

    setup() {
        this._super(...arguments);

        this.rpc = useService("rpc");
        this.ui = useService("ui");
    },

    async _onProductTemplateUpdate() {
        this._super(...arguments);
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                await this.props.record.update({
                    product_id: [result.product_id, 'whatever'],
                });
                if (result.has_optional_products) {
                    this._openProductConfigurator('options');
                } else {
                    this._onProductUpdate();
                }
            }
        } else {
            if (!result.mode || result.mode === 'configurator') {
                this._openProductConfigurator('add');
            } else {
                // only triggered when sale_product_matrix is installed.
                this._openGridConfigurator(result.mode);
            }
        }
    },

    _editProductConfiguration() {
        this._super(...arguments);
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator('edit');
        }
    },

    get isConfigurableTemplate() {
        return this._super(...arguments) || this.props.record.data.is_configurable_product;
    },

    async _openProductConfigurator(mode) {
        const saleOrderRecord = this.props.record.model.root;
        const pricelistId = saleOrderRecord.data.pricelist_id ? saleOrderRecord.data.pricelist_id[0] : false;
        const productTemplateId = this.props.record.data.product_template_id[0];
        const $modal = $(
            await this.rpc(
                "/sale_product_configurator/configure",
                {
                    product_template_id: productTemplateId,
                    quantity: this.props.record.data.product_uom_qty || 1,
                    pricelist_id: pricelistId,
                    product_template_attribute_value_ids: this.props.record.data.product_template_attribute_value_ids.records.map(
                        record => record.data.id
                    ),
                    product_no_variant_attribute_value_ids: this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                        record => record.data.id
                    ),
                    context: this.props.record.context,
                },
            )
        );
        const productSelector = `input[type="hidden"][name="product_id"], input[type="radio"][name="product_id"]:checked`;
        // TODO VFE drop this selectOrCreate and make it so that
        // get_single_product_variant returns first variant as well.
        // and use specified product on edition mode.
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
        const customAttributeValues = this.props.record.data.product_custom_attribute_value_ids.records.map(
            record => {
                // NOTE: this dumb formatting is necessary to avoid
                // modifying the shared code between frontend & backend for now.
                return {
                    custom_value: record.data.custom_value,
                    custom_product_template_attribute_value_id: {
                        res_id: record.data.custom_product_template_attribute_value_id[0],
                    },
                };
            }
        );
        this.rootProduct = {
            product_id: productId,
            product_template_id: productTemplateId,
            quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
            variant_values: variantValues,
            product_custom_attribute_values: customAttributeValues,
            no_variant_attribute_values: noVariantAttributeValues,
        };
        const optionalProductsModal = new OptionalProductsModal(null, {
            rootProduct: this.rootProduct,
            pricelistId: pricelistId,
            okButtonText: this.env._t("Confirm"),
            cancelButtonText: this.env._t("Back"),
            title: this.env._t("Configure"),
            context: this.props.record.context,
            mode: mode,
        });
        let modalEl;
        optionalProductsModal.opened(() => {
            modalEl = optionalProductsModal.el;
            this.ui.activateElement(modalEl);
        });
        optionalProductsModal.on("closed", null, async () => {
            // Wait for the event that caused the close to bubble
            await new Promise(resolve => setTimeout(resolve, 0));
            this.ui.deactivateElement(modalEl);
        });
        optionalProductsModal.open();

        let confirmed = false;
        optionalProductsModal.on("confirm", null, async () => {
            confirmed = true;
            const [
                mainProduct,
                ...optionalProducts
            ] = await optionalProductsModal.getAndCreateSelectedProducts();

            await this.props.record.update(this._convertConfiguratorDataToUpdateData(mainProduct));
            this._onProductUpdate();
            const optionalProductLinesCreationContext = this._convertConfiguratorDataToLinesCreationContext(optionalProducts);
            for (let optionalProductLineCreationContext of optionalProductLinesCreationContext) {
                const line = await saleOrderRecord.data.order_line.addNew({
                    position: 'bottom',
                    context: optionalProductLineCreationContext,
                    mode: 'readonly',  // whatever but not edit !
                });
                // FIXME: update sets the field dirty otherwise on the next edit and click out it gets deleted
                line.update({ sequence: line.data.sequence });
            }
            saleOrderRecord.data.order_line.unselectRecord();
        });
        optionalProductsModal.on("closed", null, () => {
            if (confirmed) {
                return;
            }
            if (mode != 'edit') {
                this.props.record.update({
                    product_template_id: false,
                    product_id: false,
                    product_uom_qty: 1.0,
                    // TODO reset custom/novariant values (and remove onchange logic?)
                });
            }
        });
    },

    _convertConfiguratorDataToUpdateData(mainProduct) {
        let result = {
            // TODO find a way to get the real product name
            // bc 'whatever' is really displayed when showing the 'Product Variant' column
            product_id: [mainProduct.product_id, 'whatever'],
            product_uom_qty: mainProduct.quantity,
        };
        var customAttributeValues = mainProduct.product_custom_attribute_values;
        var customValuesCommands = [{ operation: "DELETE_ALL" }];
        if (customAttributeValues && customAttributeValues.length !== 0) {
            _.each(customAttributeValues, function (customValue) {
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

        result.product_custom_attribute_value_ids = {
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

        result.product_no_variant_attribute_value_ids = {
            operation: "MULTI",
            commands: noVariantCommands,
        };

        return result;
    },

    /**
     * Will map the optional producs data to sale.order.line
     * creation contexts.
     *
     * @param {Array} optionalProductsData The optional products data given by the configurator
     *
     * @private
     */
    _convertConfiguratorDataToLinesCreationContext: function (optionalProductsData) {
        return optionalProductsData.map(productData => {
            return {
                default_product_id: productData.product_id,
                default_product_template_id: productData.product_template_id,
                default_product_uom_qty: productData.quantity,
                default_product_no_variant_attribute_value_ids: productData.no_variant_attribute_values.map(
                    noVariantAttributeData => {
                        return [4, parseInt(noVariantAttributeData.value)];
                    }
                ),
                default_product_custom_attribute_value_ids: productData.product_custom_attribute_values.map(
                    customAttributeData => {
                        return [
                            0,
                            0,
                            {
                                custom_product_template_attribute_value_id:
                                    customAttributeData.custom_product_template_attribute_value_id,
                                custom_value: customAttributeData.custom_value,
                            },
                        ];
                    }
                )
            };
        });
    },
});
