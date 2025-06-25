/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useEffect } from '@odoo/owl';
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { useService } from "@web/core/utils/hooks";
import {
    ProductLabelSectionAndNoteField,
    productLabelSectionAndNoteField,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog";
import { uuid } from "@web/views/utils";
import { ComboConfiguratorDialog } from "./combo_configurator_dialog/combo_configurator_dialog";
import { ProductCombo } from "./models/product_combo";
import { getLinkedSaleOrderLines, serializeComboItem, getSelectedCustomPtav } from "./sale_utils";

async function applyProduct(record, product) {
    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]),  // Command.clear isn't supported in static_list/_applyCommands
    ];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = getSelectedCustomPtav(ptal);
        if (selectedCustomPTAV) {
            customAttributesCommands.push(
                x2ManyCommands.create(undefined, {
                    custom_product_template_attribute_value_id: [selectedCustomPTAV.id, "we don't care"],
                    custom_value: ptal.customValue,
                })
            );
        };
    }

    const noVariantPTAVIds = product.attribute_lines.filter(
        ptal => ptal.create_variant === "no_variant"
    ).flatMap(ptal => ptal.selected_attribute_value_ids);

    // We use `_update` (not locked) instead of `update` (locked) so that multiple records can be
    // updated in parallel (for performance).
    await record._update({
        product_id: [product.id, product.display_name],
        product_uom_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
    });
};


export class SaleOrderLineProductField extends ProductLabelSectionAndNoteField {
    static template = "sale.SaleProductField";
    static props = {
        ...ProductLabelSectionAndNoteField.props,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm")
        let isMounted = false;
        let isInternalUpdate = false;
        let wasCombo = false;
        const { updateRecord } = this;
        this.updateRecord = (value) => {
            isInternalUpdate = true;
            wasCombo = this.isCombo;
            return updateRecord.call(this, value);
        };
        useEffect(value => {
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
                if (wasCombo) {
                    // If the previously selected product was a combo, delete its selected combo
                    // items before changing the product.
                    this.props.record.update({ selected_combo_items: JSON.stringify([]) });
                }
                if (this.relation === "product.template" || this.isCombo) {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

    get productName() {
        if (this.props.name == 'product_template_id') {
            const product_id_data = this.props.record.data.product_id;
            if (product_id_data && product_id_data[1]) {
                return product_id_data[1].split("\n")[0];
            }
        }
        return super.productName
    }
    get isProductClickable() {
        // product form should be accessible if the widget field is readonly
        // or if the line cannot be edited (e.g. locked SO)
        return (
            this.props.readonlyField ||
            (this.props.record.model.root.activeFields.order_line &&
                this.props.record.model.root._isReadonly("order_line"))
        );
    }
    get hasExternalButton() {
        // Keep external button, even if field is specified as 'no_open' so that the user is not
        // redirected to the product when clicking on the field content
        const res = super.hasExternalButton;
        return res || (!!this.props.record.data[this.props.name] && !this.state.isFloating);
    }
    get hasConfigurationButton() {
        return this.isConfigurableLine || this.isConfigurableTemplate || this.isCombo;
    }
    get isConfigurableLine() {
        return false;
    }
    get isConfigurableTemplate() {
        return this.props.record.data.is_configurable_product;
    }
    get isCombo() {
        return this.props.record.data.product_type === 'combo';
    }
    get isDownpayment() {
        return this.props.record.data.is_downpayment;
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }

    /**
     * @override
     */
    get sectionAndNoteClasses() {
        const className = super.sectionAndNoteClasses;
        if (!className && !this.productName && !this.isDownpayment) {
            return "text-warning";
        }
        return className;
    }

    onClick(ev) {
        // Override to get internal link to products in SOL that cannot be edited
        if (this.props.readonly) {
            ev.stopPropagation();
            this.openAction();
        } else {
            super.onClick(ev);
        }
    }

    async _onProductTemplateUpdate() {
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
                if (result.is_combo) {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    this._openComboConfigurator();
                } else if (result.has_optional_products) {
                    this._openProductConfigurator();
                } else {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    this._onProductUpdate();
                }
            }
        } else {
            if (result && result.sale_warning) {
                const {type, title, message} = result.sale_warning
                if (type === 'block') {
                    // display warning block, and remove blocking product
                    this.dialog.add(WarningDialog, { title, message });
                    this.props.record.update({'product_template_id': false})
                    return
                } else if (type == 'warning') {
                    // show the warning but proceed with the configurator opening
                    this.notification.add(message, {
                        title,
                        type: "warning",
                    });
                }
            }
            if (!result.mode || result.mode === 'configurator') {
                this._openProductConfigurator();
            } else {
                // only triggered when sale_product_matrix is installed.
                this._openGridConfigurator();
            }
        }
    }

    async _onProductUpdate() {} // event_booth_sale, event_sale, sale_renting

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else if (this.isCombo) {
            this._openComboConfigurator(true);
        } else if (this.isConfigurableTemplate) {
            this._openProductConfigurator(true);
        }
    }
    _editLineConfiguration() {} // event_booth_sale, event_sale, sale_renting

    async _openProductConfigurator(edit=false) {
        const saleOrderRecord = this.props.record.model.root;
        const saleOrderLine = this.props.record.data;
        let ptavIds = this._getVariantPtavIds(saleOrderLine);
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
            productTemplateId: saleOrderLine.product_template_id[0],
            ptavIds: ptavIds,
            customPtavs: customPtavs,
            quantity: saleOrderLine.product_uom_qty,
            productUOMId: saleOrderLine.product_uom[0],
            companyId: saleOrderRecord.data.company_id[0],
            pricelistId: saleOrderRecord.data.pricelist_id[0],
            currencyId: saleOrderLine.currency_id[0],
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
            edit: edit,
            save: async (mainProduct, optionalProducts) => {
                await Promise.all([
                    applyProduct(this.props.record, mainProduct),
                    ...optionalProducts.map(async product => {
                        const line = await saleOrderRecord.data.order_line.addNewRecord({
                            position: 'bottom', mode: 'readonly'
                        });
                        await applyProduct(line, product);
                    }),
                ]);
                this._onProductUpdate();
                saleOrderRecord.data.order_line.leaveEditMode();
            },
            discard: () => {
                saleOrderRecord.data.order_line.delete(this.props.record);
            },
            ...this._getAdditionalDialogProps(),
        });
    }

    async _openComboConfigurator(edit=false) {
        const saleOrder = this.props.record.model.root.data;
        const comboLineRecord = this.props.record;
        const comboItemLineRecords = getLinkedSaleOrderLines(comboLineRecord);
        const selectedComboItems = await Promise.all(comboItemLineRecords.map(async record => ({
            id: record.data.combo_item_id[0],
            no_variant_ptav_ids: edit ? this._getNoVariantPtavIds(record.data) : [],
            custom_ptavs: edit ? await this._getCustomPtavs(record.data) : [],
        })));
        const { combos, ...remainingData } = await rpc('/sale/combo_configurator/get_data', {
            product_tmpl_id: comboLineRecord.data.product_template_id[0],
            currency_id: comboLineRecord.data.currency_id[0],
            quantity: comboLineRecord.data.product_uom_qty,
            date: serializeDateTime(saleOrder.date_order),
            company_id: saleOrder.company_id[0],
            pricelist_id: saleOrder.pricelist_id[0],
            selected_combo_items: selectedComboItems,
            ...this._getAdditionalRpcParams(),
        });
        this.dialog.add(ComboConfiguratorDialog, {
            combos: combos.map(combo => new ProductCombo(combo)),
            ...remainingData,
            company_id: saleOrder.company_id[0],
            pricelist_id: saleOrder.pricelist_id[0],
            date: serializeDateTime(saleOrder.date_order),
            edit: edit,
            save: async (comboProductData, selectedComboItems) => {
                saleOrder.order_line.leaveEditMode();
                const comboLineValues = {
                    product_uom_qty: comboProductData.quantity,
                    selected_combo_items: JSON.stringify(
                        selectedComboItems.map(serializeComboItem)
                    ),
                };
                if (!edit) {
                    comboLineValues.virtual_id = uuid();
                }
                await comboLineRecord.update(comboLineValues);
                // Ensure that the order lines are sorted according to their sequence.
                await saleOrder.order_line._sort();
            },
            discard: () => saleOrder.order_line.delete(comboLineRecord),
            ...this._getAdditionalDialogProps(),
        });
    }

    /**
     * Hook to append additional RPC params in overriding modules.
     *
     * @return {Object} The additional RPC params.
     */
    _getAdditionalRpcParams() {
        return {};
    }

    /**
     * Hook to append additional props in overriding modules.
     *
     * @return {Object} The additional props.
     */
    _getAdditionalDialogProps() {
        return {};
    }

    /**
     * Return the PTAV ids of the provided sale order line.
     *
     * @param saleOrderLine The sale order line
     * @return {Number[]} The sale order line's PTAV ids.
     */
    _getVariantPtavIds(saleOrderLine) {
        return saleOrderLine.product_template_attribute_value_ids.records.map(
            record => record.resId
        );
    }

    /**
     * Return the `no_variant` PTAV ids of the provided sale order line.
     *
     * @param saleOrderLine The sale order line
     * @return {Number[]} The sale order line's `no_variant` PTAV ids.
     */
    _getNoVariantPtavIds(saleOrderLine) {
        return saleOrderLine.product_no_variant_attribute_value_ids.records.map(
            record => record.resId
        );
    }

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
        const customPtavs = customPtavIds.records[0]?.isNew
            ? customPtavIds.records.map(record => record.data)
            : customPtavIds.currentIds.length
                ? await this.orm.read(
                    'product.attribute.custom.value',
                    customPtavIds.currentIds,
                    ['custom_product_template_attribute_value_id', 'custom_value'],
                )
                : [];
        return customPtavs.map(customPtav => ({
            id: customPtav.custom_product_template_attribute_value_id[0],
            value: customPtav.custom_value,
        }));
    }
}

export const saleOrderLineProductField = {
    ...productLabelSectionAndNoteField,
    component: SaleOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = productLabelSectionAndNoteField.extractProps(...arguments);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category("fields").add("sol_product_many2one", saleOrderLineProductField);
