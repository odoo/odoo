import { useService } from "@web/core/utils/hooks";
import { serializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { rpc } from "@web/core/network/rpc";
import { x2ManyCommands } from "@web/core/orm_plugin";
import { uuid } from "@web/core/utils/strings";
import { ComboConfiguratorDialog } from "./combo_configurator_dialog/combo_configurator_dialog";
import { ProductCombo } from "./models/product_combo";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog";
import { getLinkedSaleOrderLines, serializeComboItem, getSelectedCustomPtav } from "./sale_utils";

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

    async _onProductTemplateUpdate() {
        super._onProductTemplateUpdate();
        const result = await this.orm.call(
            "product.template",
            "get_single_product_variant",
            [this.props.record.data.product_template_id.id],
            {
                context: this.props.context,
            }
        );
        if (result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                if (result.is_combo) {
                    await this.props.record.update({
                        product_id: { id: result.product_id, display_name: result.product_name },
                    });
                    this._openComboConfigurator(false, result.has_optional_products);
                } else if (result.has_optional_products) {
                    this._openProductConfigurator();
                } else {
                    await this.props.record.update({
                        product_id: { id: result.product_id, display_name: result.product_name },
                    });
                    this._onProductUpdate();
                }
            }
        } else if (!result.mode || result.mode === "configurator") {
            this._openProductConfigurator();
        } else {
            // only triggered when sale_product_matrix is installed.
            this._openGridConfigurator();
        }
    },

    _openGridConfigurator(edit = false) {}, // sale_product_matrix

    async _onProductUpdate() {}, // event_booth_sale, event_sale, sale_renting

    onEditConfiguration() {
        super.onEditConfiguration();
        if (this.isCombo) {
            this._openComboConfigurator(true);
        } else if (this.isConfigurableTemplate) {
            this._openProductConfigurator(true);
        }
    },

    async _openProductConfigurator(edit = false, selectedComboItems = []) {
        const saleOrderRecord = this.props.record.model.root;
        const saleOrderLine = this.props.record.data;
        const ptavIds = [...this._getVariantPtavIds(saleOrderLine)];
        let customPtavs = [];

        if (edit) {
            /**
             * no_variant and custom attribute don't need to be given to the configurator for new
             * products.
             */
            ptavIds.push(...this._getNoVariantPtavIds(saleOrderLine));
            customPtavs = await this._getCustomPtavs(saleOrderLine);
        }

        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: saleOrderLine.product_template_id.id,
            ptavIds: ptavIds,
            customPtavs: customPtavs,
            quantity: saleOrderLine.product_uom_qty,
            productUOMId: saleOrderLine.product_uom_id.id,
            companyId: saleOrderRecord.data.company_id.id,
            pricelistId: saleOrderRecord.data.pricelist_id.id,
            currencyId: saleOrderLine.currency_id.id,
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
            selectedComboItems: selectedComboItems,
            edit: edit,
            save: async (mainProduct, optionalProducts) => {
                // Don't add main product if it's a combo product as it has already been added
                // from combo configurator
                const proms = !selectedComboItems.length
                    ? [applyProduct(this.props.record, mainProduct)]
                    : [];

                for (const [i, product] of optionalProducts.entries()) {
                    const index =
                        saleOrderRecord.data.order_line.records.indexOf(this.props.record)
                        + selectedComboItems.length
                        + i;
                    const line = await saleOrderRecord.data.order_line.addNewRecordAtIndex(index, {
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
                    saleOrderRecord.data.order_line.delete(this.props.record);
                }
            },
            ...this._getAdditionalDialogProps(),
        });
    },

    async _openComboConfigurator(edit = false, hasOptionalProducts = false) {
        const saleOrder = this.props.record.model.root.data;
        const comboLineRecord = this.props.record;
        const comboItemLineRecords = getLinkedSaleOrderLines(comboLineRecord).filter(record => !!record.data.combo_item_id);
        const selectedComboItems = await Promise.all(comboItemLineRecords.map(async record => ({
            id: record.data.combo_item_id.id,
            no_variant_ptav_ids: edit ? this._getNoVariantPtavIds(record.data) : [],
            custom_ptavs: edit ? await this._getCustomPtavs(record.data) : [],
        })));
        const { combos, ...remainingData } = await rpc('/sale/combo_configurator/get_data', {
            product_tmpl_id: comboLineRecord.data.product_template_id.id,
            currency_id: comboLineRecord.data.currency_id.id,
            quantity: comboLineRecord.data.product_uom_qty,
            date: serializeDateTime(saleOrder.date_order),
            company_id: saleOrder.company_id.id,
            pricelist_id: saleOrder.pricelist_id.id,
            selected_combo_items: selectedComboItems,
            ...this._getAdditionalRpcParams(),
        });

        const comboChoices = combos.map(combo => new ProductCombo(combo));
        const preselectedComboItems = comboChoices
            .map(combo => combo.preselectedComboItem)
            .filter(Boolean);
        if (preselectedComboItems.length === comboChoices.length) {
            return this.handleComboSave(
                { 'quantity': remainingData.quantity },
                preselectedComboItems,
                edit,
                hasOptionalProducts
            );
        }
        this.dialog.add(ComboConfiguratorDialog, {
            combos: comboChoices,
            ...remainingData,
            company_id: saleOrder.company_id.id,
            pricelist_id: saleOrder.pricelist_id.id,
            date: serializeDateTime(saleOrder.date_order),
            edit: edit,
            save: async (comboProductData, selectedComboItems) => {
                this.handleComboSave(
                    comboProductData,
                    selectedComboItems,
                    edit,
                    hasOptionalProducts
                );
            },
            discard: () => saleOrder.order_line.delete(comboLineRecord),
            ...this._getAdditionalDialogProps(),
        });
    },

    async handleComboSave(comboProductData, selectedComboItems, edit, hasOptionalProducts) {
        const saleOrder = this.props.record.model.root.data;
        const comboLineRecord = this.props.record;
        saleOrder.order_line.leaveEditMode();
        const comboLineValues = {
            product_uom_qty: comboProductData.quantity,
            selected_combo_items: JSON.stringify(selectedComboItems.map(serializeComboItem)),
        };
        if (!edit) {
            comboLineValues.virtual_id = uuid();
        }
        await comboLineRecord.update(comboLineValues);
        // Ensure that the order lines are sorted according to their sequence.
        await saleOrder.order_line._sort();

        if (hasOptionalProducts && !edit) {
            const selectedComboProducts = selectedComboItems.map(
                item => ({ name: item.product.display_name })
            );
            await this._openProductConfigurator(false, selectedComboProducts);
        }
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

    /**
     * Return the `no_variant` PTAV ids of the provided sale order line.
     *
     * @param saleOrderLine The sale order line
     * @return {Number[]} The sale order line's `no_variant` PTAV ids.
     */
    _getNoVariantPtavIds(saleOrderLine) {
        return saleOrderLine.product_no_variant_attribute_value_ids.currentIds;
    },

    /**
     * Return the custom PTAVs of the provided sale order line.
     *
     * @param saleOrderLine The sale order line
     * @return {Promise<CustomPtav[]>} The sale order line's custom PTAVs.
     */
    async _getCustomPtavs(saleOrderLine) {
        // `product.attribute.custom.value` records are not loaded in the view because sub templates
        // are not loaded in list views. Therefore, we fetch them from the server if the record was
        // saved. Otherwise, we use the value stored on the line.
        const customPtavIds = saleOrderLine.product_custom_attribute_value_ids;
        let customPtavs = [];
        if (customPtavIds.records[0]?.isNew) {
            customPtavs = customPtavIds.records.map(record => record.data);
        } else if (customPtavIds.currentIds.length) {
            const specification = {
                custom_product_template_attribute_value_id: {
                    fields: { id: {} },
                },
                custom_value: {},
            };
            customPtavs = await this.orm.webRead(
                'product.attribute.custom.value',
                customPtavIds.currentIds,
                { specification },
            );
        }
        return customPtavs.map(customPtav => ({
            id: customPtav.custom_product_template_attribute_value_id &&
                customPtav.custom_product_template_attribute_value_id.id,
            value: customPtav.custom_value,
        }));
    },
});
