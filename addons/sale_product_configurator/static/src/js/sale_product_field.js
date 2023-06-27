/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { serializeDateTime } from "@web/core/l10n/dates";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog";

patch(SaleOrderLineProductField.prototype, 'sale_product_configurator', {

    setup() {
        this._super(...arguments);

<<<<<<< HEAD
        this.dialog = useService("dialog");
        this.orm = useService("orm");
||||||| parent of b7df9864080 (temp)
        this.rpc = useService("rpc");
        this.ui = useService("ui");
=======
        this.rpc = useService("rpc");
        this.ui = useService("ui");
        this.orm = useService("orm");
>>>>>>> b7df9864080 (temp)
    },

    async _onProductTemplateUpdate() {
        this._super(...arguments);
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
            {
                context: this.context,
            }
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                await this.props.record.update({
                    product_id: [result.product_id, result.product_name],
                });
                if (result.has_optional_products) {
                    this._openProductConfigurator();
                } else {
                    this._onProductUpdate();
                }
            }
        } else {
            if (!result.mode || result.mode === 'configurator') {
                this._openProductConfigurator();
            } else {
                // only triggered when sale_product_matrix is installed.
                this._openGridConfigurator();
            }
        }
    },

    _editProductConfiguration() {
        this._super(...arguments);
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator(true);
        }
    },

    get isConfigurableTemplate() {
        return this._super(...arguments) || this.props.record.data.is_configurable_product;
    },

    async _openProductConfigurator(edit=false) {
        const saleOrderRecord = this.props.record.model.root;
<<<<<<< HEAD
||||||| parent of b7df9864080 (temp)
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
                    context: this.context,
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
            context: this.context,
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
=======
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
                    context: this.context,
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
        /**
         *  `product_custom_attribute_value_ids` records are not loaded in the view bc sub templates
         *  are not loaded in list views. Therefore, we fetch them from the server if the record is
         *  saved. Else we use the value stored on the line.
         */
        const customAttributeValueRecords = this.props.record.data.product_custom_attribute_value_ids.records;
        let customAttributeValues = [];
        if (customAttributeValueRecords.length > 0) {
            if (customAttributeValueRecords[0].isNew) {
                customAttributeValues = customAttributeValueRecords.map(
                    record => record.data
                );
            } else {
                customAttributeValues = await this.orm.read(
                    'product.attribute.custom.value',
                    this.props.record.data.product_custom_attribute_value_ids.currentIds,
                    ["custom_product_template_attribute_value_id", "custom_value"]
                );
            }
        }
        const formattedCustomAttributeValues = customAttributeValues.map(
            data => {
                // NOTE: this dumb formatting is necessary to avoid
                // modifying the shared code between frontend & backend for now.
                return {
                    custom_value: data.custom_value,
                    custom_product_template_attribute_value_id: {
                        res_id: data.custom_product_template_attribute_value_id[0],
                    },
                };
            }
        );
        this.rootProduct = {
            product_id: productId,
            product_template_id: productTemplateId,
            quantity: parseFloat($modal.find('input[name="add_qty"]').val() || 1),
            variant_values: variantValues,
            product_custom_attribute_values: formattedCustomAttributeValues,
            no_variant_attribute_values: noVariantAttributeValues,
        };
        const optionalProductsModal = new OptionalProductsModal(null, {
            rootProduct: this.rootProduct,
            pricelistId: pricelistId,
            okButtonText: this.env._t("Confirm"),
            cancelButtonText: this.env._t("Back"),
            title: this.env._t("Configure"),
            context: this.context,
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
>>>>>>> b7df9864080 (temp)

        /**
         *  `product_custom_attribute_value_ids` records are not loaded in the view bc sub templates
         *  are not loaded in list views. Therefore, we fetch them from the server if the record is
         *  saved. Else we use the value stored on the line.
         */
        const customAttributeValues =
            this.props.record.data.product_custom_attribute_value_ids.records[0]?.isNew ?
            this.props.record.data.product_custom_attribute_value_ids.records.map(
                record => record.data
            ) :
            await this.orm.read(
                'product.attribute.custom.value',
                this.props.record.data.product_custom_attribute_value_ids.currentIds,
                ["custom_product_template_attribute_value_id", "custom_value"]
            );
        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: this.props.record.data.product_template_id[0],
            ptavIds: this.props.record.data.product_template_attribute_value_ids.records.map(
                record => record.data.id
            ).concat(this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                record => record.data.id
            )),
            customAttributeValues: customAttributeValues.map(
                data => {
                    return {
                        ptavId: data.custom_product_template_attribute_value_id[0],
                        value: data.custom_value,
                    }
                }
            ),
            quantity: this.props.record.data.product_uom_qty,
            productUOMId: this.props.record.data.product_uom[0],
            companyId: saleOrderRecord.data.company_id[0],
            pricelistId: saleOrderRecord.data.pricelist_id[0],
            currencyId: this.props.record.data.currency_id[0],
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
            edit: edit,
            save: async (mainProduct, optionalProducts) => {
                await this.props.record.update(mainProduct);
                this._onProductUpdate();
                for (const optionalProduct of optionalProducts) {
                    const line = await saleOrderRecord.data.order_line.addNew({
                        position: 'bottom',
                    });
                    line.update(optionalProduct);
                }
                saleOrderRecord.data.order_line.unselectRecord();
            },
            discard: () => {
                saleOrderRecord.data.order_line.removeRecord(this.props.record);
            },
        });
    },
});
