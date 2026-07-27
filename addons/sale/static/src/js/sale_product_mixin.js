import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog";
import { getCustomPtavs, getNoVariantPtavIds, getSelectedComboItems, getSelectedCustomPtav } from "./sale_utils";
import { openComboConfigurator } from "./combo_configurator_utils";

async function applyProduct(record, product) {
    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]), // Command.clear isn't supported in static_list/_applyCommands
    ];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = getSelectedCustomPtav(ptal);
        if (selectedCustomPTAV) {
            customAttributesCommands.push(
                x2ManyCommands.create(undefined, {
                    custom_product_template_attribute_value_id: [
                        selectedCustomPTAV.id,
                        "we don't care",
                    ],
                    custom_value: ptal.customValue,
                })
            );
        }
    }

    const noVariantPTAVIds = product.attribute_lines
        .filter((ptal) => ptal.create_variant === "no_variant")
        .flatMap((ptal) => ptal.selected_attribute_value_ids);

    // We use `_update` (not locked) instead of `update` (locked) so that multiple records can be
    // updated in parallel (for performance).
    const update_values = {
        product_id: { id: product.id, display_name: product.display_name },
        product_uom_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
    };
    if (product.uom) {
        // only update uom field if uom are enabled (uom_data provided), otherwise we don't have the display_name
        // and the value isn't expected to change anyway.
        update_values.product_uom_id = product.uom;
    }
    await record._update(update_values);
}

export const saleProductMixin = () => ({
    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.orm = useService("orm");
    },

    get isCombo() {
        return (
            this.props.record.data.product_template_id &&
            this.props.record.data.product_type === "combo"
        );
    },

    get hasConfigurationButton() {
        return this.isConfigurableTemplate || this.isCombo;
    },

    get isConfigurableTemplate() {
        return this.props.record.data.is_configurable_product;
    },

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    },

    async _getProductConfiguratorData(edit = false) {
        const saleOrder = this.props.record.model.root.data;
        const saleOrderLine = this.props.record.data;
        const ptavIds = [...this._getVariantPtavIds(saleOrderLine)];
        let productUOMId;
        if (edit) {
            // no_variant attributes don't need to be given to the configurator for new products.
            ptavIds.push(...getNoVariantPtavIds(saleOrderLine));
            productUOMId = saleOrderLine.product_uom_id.id;
        }
        return rpc('/sale/product_configurator/get_values',
            {
                product_template_id: saleOrderLine.product_template_id.id,
                quantity: saleOrderLine.product_uom_qty,
                currency_id: saleOrderLine.currency_id?.id,
                so_date: this._getSoDate(),
                product_uom_id: productUOMId,
                company_id: saleOrder.company_id?.id,
                pricelist_id: saleOrder.pricelist_id?.id,
                ptav_ids: ptavIds,
                only_main_product: edit,
                ...this._getAdditionalRpcParams(),
            });
    },

    async _onProductTemplateUpdate() {
        super._onProductTemplateUpdate();
        const data = await this._getProductConfiguratorData();
        if (data && data.product_id) {
            if (this.props.record.data.product_id != data.product_id.id) {
                if (data.is_combo) {
                    await this.props.record.update({
                        product_id: { id: data.product_id, display_name: data.product_name },
                    });
                    this._openComboConfigurator({edit: false, data: data});
                } else if (data.has_optional_products) {
                    this._openProductConfigurator({ data: data });
                } else {
                    await this.props.record.update({
                        product_id: { id: data.product_id, display_name: data.product_name },
                    });
                    this._onProductUpdate();
                }
            }
        } else if (!data.mode || data.mode === 'configurator' || !this._useGridConfigurator()) {
            this._openProductConfigurator({ data: data });
        } else {
            // only triggered when sale_product_matrix is installed.
            this._openGridConfigurator();
        }
    },

    /**
     * Hook to decide whether the grid/matrix product selector should be used when available,
     * instead of the regular configurator dialog.
     */
    _useGridConfigurator() {
        return true;
    },

    _openGridConfigurator(edit = false) {}, // sale_product_matrix

    async _onProductUpdate() {}, // event_booth_sale, event_sale, sale_renting

    async onEditConfiguration() {
        super.onEditConfiguration();
        if (this.isCombo) {
            this._openComboConfigurator({edit: true});
        } else if (this.isConfigurableTemplate) {
            const data = await this._getProductConfiguratorData(true)
            this._openProductConfigurator({edit: true, data: data});
        }
    },

    async _openProductConfigurator({ edit = false, selectedComboItems = [], data } = {}) {
        const saleOrder = this.props.record.model.root.data;
        const saleOrderLine = this.props.record.data;
        let customPtavs = [];

        if (edit) {
            // custom attributes don't need to be given to the configurator for new products.
            customPtavs = await getCustomPtavs(this.orm, saleOrderLine);
        }
        const { products, optional_products } = data;
        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: saleOrderLine.product_template_id.id,
            products: products,
            optionalProducts: optional_products,
            customPtavs: customPtavs,
            companyId: saleOrder.company_id?.id,
            pricelistId: saleOrder.pricelist_id?.id,
            currencyId: saleOrderLine.currency_id?.id,
            soDate: this._getSoDate(),
            selectedComboItems: selectedComboItems,
            edit: edit,
            save: async (mainProduct, optionalProducts) => {
                // Don't add main product if it's a combo product as it has already been added
                // from combo configurator
                const proms = !selectedComboItems.length
                    ? [applyProduct(this.props.record, mainProduct)]
                    : [];

                const orderLines = this._getOrderLines();
                for (const [i, product] of optionalProducts.entries()) {
                    const index =
                        orderLines.records.indexOf(this.props.record)
                        + selectedComboItems.length
                        + i;
                    const line = await orderLines.addNewRecordAtIndex(index, {
                        mode: 'readonly',
                    });
                    const productData = this._prepareNewLineData(line, product);
                    proms.push(applyProduct(line, productData));
                }

                await Promise.all(proms);
                this._onProductUpdate();
            },
            discard: () => {
                if (!selectedComboItems.length) {
                    // Don't delete the main product if it's a combo product as it has been added
                    // from combo configurator
                    this._getOrderLines().delete(this.props.record);
                }
            },
            ...this._getAdditionalDialogProps(),
        });
    },

    async _openComboConfigurator({ edit = false, data } = {}) {
        const comboLineRecord = this.props.record;
        const selectedComboItems = await getSelectedComboItems(this.orm, comboLineRecord, edit);

        await openComboConfigurator({
            dialog: this.dialog,
            comboLineRecord,
            edit,
            selectedComboItems,
            additionalRpcParams: this._getAdditionalRpcParams(),
            additionalDialogProps: this._getAdditionalDialogProps(),
            onSave: async (comboProductData, selectedItems) => {
                if (!edit && data.has_optional_products) {
                    const selectedComboProducts = selectedItems.map(
                        item => ({ name: item.product.display_name })
                    );
                    await this._openProductConfigurator({
                        selectedComboItems: selectedComboProducts,
                        data,
                    });
                }
            },
        });
    },

    /**
     * Hook to append additional RPC params in overriding modules.
     *
     * @return {Object} The additional RPC params.
     */
    _getAdditionalRpcParams() {
        return {};
    },

    /**
     * Hook to append additional props in overriding modules.
     *
     * @return {Object} The additional props.
     */
    _getAdditionalDialogProps() {
        return {};
    },

    /**
     * Hook to return the order lines list for the current record.
     */
    _getOrderLines() {
        return this.props.record.model.root.data.order_line;
    },

    /**
     * Hook to return the SO date for the configurator dialog.
     */
    _getSoDate() {
        return serializeDateTime(this.props.record.model.root.data.date_order);
    },

    /**
     * Hook to append extra data in newly created optional product lines.
     */
    _prepareNewLineData(_line, product) {
        return product;
    },

    /**
     * Return the PTAV ids of the provided sale order line.
     *
     * @param saleOrderLine The sale order line
     * @return {Number[]} The sale order line's PTAV ids.
     */
    _getVariantPtavIds(saleOrderLine) {
        return saleOrderLine.product_template_attribute_value_ids.currentIds;
    },
});
