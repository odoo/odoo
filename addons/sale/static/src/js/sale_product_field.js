/** @odoo-module native */
import {
    ProductLabelSectionAndNoteField,
    productLabelSectionAndNoteField,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";
import { serializeDateTime } from "@web/core/l10n/dates";
import { rpc } from "@web/core/network";
import { x2ManyCommands } from "@web/core/network";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/translation";
import { uuid } from "@web/core/utils/format/strings";
import { useService } from "@web/core/utils/hooks";
import { sortStaticList } from "@web/model/relational_model";

import { ComboConfiguratorDialog } from "./combo_configurator_dialog/combo_configurator_dialog.js";
import { ProductCombo } from "./models/product_combo.js";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog.js";
import {
    getLinkedSaleOrderLines,
    getSelectedCustomPtav,
    serializeComboItem,
} from "./sale_utils.js";

async function applyProduct(record, product) {
    const customAttributesCommands = [x2ManyCommands.clear()];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = getSelectedCustomPtav(ptal);
        if (selectedCustomPTAV) {
            customAttributesCommands.push(
                x2ManyCommands.create(undefined, {
                    custom_product_template_attribute_value_id: {
                        id: selectedCustomPTAV.id,
                        display_name: selectedCustomPTAV.name,
                    },
                    custom_value: ptal.customValue,
                }),
            );
        }
    }

    const noVariantPTAVIds = product.attribute_lines
        .filter((ptal) => ptal.create_variant === "no_variant")
        .flatMap((ptal) => ptal.selected_attribute_value_ids);

    const update_values = {
        product_id: { id: product.id, display_name: product.display_name },
        product_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
    };
    if (product.uom) {
        update_values.product_uom_id = product.uom;
    }
    await record.update(update_values);
}

export class SaleOrderLineProductField extends ProductLabelSectionAndNoteField {
    static template = "sale.SaleProductField";
    static props = {
        ...super.props,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
    }

    /**
     * @param {() => Promise<unknown>} applySelection
     * @returns {Promise<void>}
     */
    _selectProduct(applySelection) {
        const wasCombo = this.isCombo;
        const previousId = this.value && this.value.id;
        return this.props.record.model.trackCompoundUpdate(async () => {
            await applySelection();
            if (!this.value || this.value.id === previousId) {
                return;
            }
            if (wasCombo) {
                await this.props.record.update({
                    selected_combo_items: JSON.stringify([]),
                });
            }
            if (this.relation === "product.template" || this.isCombo) {
                await this._onProductTemplateUpdate();
            } else {
                await this._onProductUpdate();
            }
        });
    }

    get productName() {
        if (this.props.name === "product_template_id") {
            const product_id_data = this.props.record.data.product_id;
            if (product_id_data && product_id_data.display_name) {
                return product_id_data.display_name.split("\n")[0];
            }
        }
        return super.productName;
    }
    get isProductClickable() {
        return (
            this.props.readonlyField ||
            (this.props.record.model.root.activeFields.line_ids &&
                this.props.record.model.root.isFieldReadonly("line_ids"))
        );
    }
    get hasConfigurationButton() {
        return this.isConfigurableTemplate || this.isCombo;
    }
    get isConfigurableTemplate() {
        return this.props.record.data.is_configurable_product;
    }
    get isCombo() {
        return (
            this.props.record.data.product_template_id &&
            this.props.record.data.product_type === "combo"
        );
    }
    get isDownpayment() {
        return this.props.record.data.is_downpayment;
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }

    /** @override */
    get sectionAndNoteClasses() {
        return {
            ...super.sectionAndNoteClasses,
            "text-warning":
                !this.isSectionOrSubSection &&
                !this.isNote() &&
                !this.productName &&
                !this.isDownpayment,
        };
    }

    get label() {
        let label = this.props.record.data.name;
        if (
            this.translatedProductName &&
            label.startsWith(this.translatedProductName)
        ) {
            label = label.slice(this.translatedProductName.length + 1);
        } else {
            label = super.label;
        }
        return label;
    }

    get translatedProductName() {
        return this.props.record.data.product_name_translated;
    }

    parseLabel(value) {
        if (!this.translatedProductName) {
            return super.parseLabel(value);
        }
        return (
            (value && this.translatedProductName.concat("\n", value)) ||
            this.translatedProductName
        );
    }

    get m2oProps() {
        const p = super.m2oProps;
        const value = p.value && { ...p.value };
        if (this.isCombo && value && value.display_name) {
            value.display_name = `${value.display_name} x ${this.props.record.data.product_qty}`;
        }
        return {
            ...p,
            canOpen:
                this.props.canOpen && (!this.props.readonly || this.isProductClickable),
            update: (value) => this._selectProduct(() => p.update(value)),
            value,
        };
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    async _onProductTemplateUpdate() {
        const result = await this.orm.call(
            "product.template",
            "get_single_product_variant",
            [this.props.record.data.product_template_id.id],
            {
                context: this.context,
            },
        );
        if (result && result.product_id) {
            if (this.props.record.data.product_id?.id !== result.product_id) {
                const productValue = {
                    product_id: {
                        id: result.product_id,
                        display_name: result.product_name,
                    },
                };
                if (result.is_combo) {
                    await this.props.record.update(productValue);
                    await this._openComboConfigurator(
                        false,
                        result.has_optional_products,
                    );
                } else if (result.has_optional_products) {
                    await this._openProductConfigurator();
                } else {
                    await this.props.record.update(productValue);
                    await this._onProductUpdate();
                }
            }
        } else if (!result?.mode || result.mode === "configurator") {
            await this._openProductConfigurator();
        } else {
            await this._openGridConfigurator();
        }
    }

    async _openGridConfigurator(edit = false) {}

    async _onProductUpdate() {}

    onEditConfiguration() {
        if (this.isCombo) {
            this._openComboConfigurator(true);
        } else if (this.isConfigurableTemplate) {
            this._openProductConfigurator(true);
        }
    }

    async _openProductConfigurator(edit = false, selectedComboItems = []) {
        const saleOrderRecord = this.props.record.model.root;
        const saleOrderLine = this.props.record.data;
        const ptavIds = [...this._getVariantPtavIds(saleOrderLine)];
        let customPtavs = [];

        if (edit) {
            ptavIds.push(...this._getNoVariantPtavIds(saleOrderLine));
            customPtavs = await this._getCustomPtavs(saleOrderLine);
        }

        this.dialog.add(ProductConfiguratorDialog, {
            productTemplateId: saleOrderLine.product_template_id.id,
            ptavIds: ptavIds,
            customPtavs: customPtavs,
            quantity: saleOrderLine.product_qty,
            productUOMId: saleOrderLine.product_uom_id.id,
            companyId: saleOrderRecord.data.company_id.id,
            pricelistId: saleOrderRecord.data.pricelist_id.id,
            currencyId: saleOrderLine.currency_id.id,
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
            selectedComboItems: selectedComboItems,
            edit: edit,
            save: async (mainProduct, optionalProducts) => {
                const proms = !selectedComboItems.length
                    ? [applyProduct(this.props.record, mainProduct)]
                    : [];

                const comboLineIndex = saleOrderRecord.data.line_ids.records.indexOf(
                    this.props.record,
                );
                for (const [i, product] of optionalProducts.entries()) {
                    const index = comboLineIndex + selectedComboItems.length + i;
                    const line =
                        await saleOrderRecord.data.line_ids.addNewRecordAtIndex(index, {
                            mode: "readonly",
                        });
                    const productData = this._prepareNewLineData(line, product);
                    proms.push(applyProduct(line, productData));
                }

                await Promise.all(proms);
                await this._onProductUpdate();
                saleOrderRecord.data.line_ids.leaveEditMode();
            },
            discard: () => {
                if (!selectedComboItems.length) {
                    saleOrderRecord.data.line_ids.delete(this.props.record);
                }
            },
            ...this._getAdditionalDialogProps(),
        });
    }

    async _openComboConfigurator(edit = false, hasOptionalProducts = false) {
        const saleOrder = this.props.record.model.root.data;
        const comboLineRecord = this.props.record;
        const comboItemLineRecords = getLinkedSaleOrderLines(comboLineRecord).filter(
            (record) => !!record.data.combo_item_id,
        );
        const selectedComboItems = await Promise.all(
            comboItemLineRecords.map(async (record) => ({
                id: record.data.combo_item_id.id,
                no_variant_ptav_ids: edit ? this._getNoVariantPtavIds(record.data) : [],
                custom_ptavs: edit ? await this._getCustomPtavs(record.data) : [],
            })),
        );
        const { combos, ...remainingData } = await rpc(
            "/sale/combo_configurator/get_data",
            {
                product_tmpl_id: comboLineRecord.data.product_template_id.id,
                currency_id: comboLineRecord.data.currency_id.id,
                quantity: comboLineRecord.data.product_qty,
                date: serializeDateTime(saleOrder.date_order),
                company_id: saleOrder.company_id.id,
                pricelist_id: saleOrder.pricelist_id.id,
                selected_combo_items: selectedComboItems,
                ...this._getAdditionalRpcParams(),
            },
        );

        const comboChoices = combos.map((combo) => new ProductCombo(combo));
        const preselectedComboItems = comboChoices
            .map((combo) => combo.preselectedComboItem)
            .filter(Boolean);
        if (preselectedComboItems.length === comboChoices.length) {
            return this.handleComboSave(
                { quantity: remainingData.quantity },
                preselectedComboItems,
                edit,
                hasOptionalProducts,
            );
        }
        this.dialog.add(ComboConfiguratorDialog, {
            combos: comboChoices,
            ...remainingData,
            company_id: saleOrder.company_id.id,
            pricelist_id: saleOrder.pricelist_id.id,
            date: serializeDateTime(saleOrder.date_order),
            edit: edit,
            save: (comboProductData, selectedComboItems) =>
                this.handleComboSave(
                    comboProductData,
                    selectedComboItems,
                    edit,
                    hasOptionalProducts,
                ),
            discard: () => saleOrder.line_ids.delete(comboLineRecord),
            ...this._getAdditionalDialogProps(),
        });
    }

    async handleComboSave(
        comboProductData,
        selectedComboItems,
        edit,
        hasOptionalProducts,
    ) {
        const saleOrder = this.props.record.model.root.data;
        const comboLineRecord = this.props.record;
        saleOrder.line_ids.leaveEditMode();
        const comboLineValues = {
            product_qty: comboProductData.quantity,
            selected_combo_items: JSON.stringify(
                selectedComboItems.map(serializeComboItem),
            ),
        };
        if (!edit) {
            comboLineValues.virtual_id = uuid();
        }
        await comboLineRecord.update(comboLineValues);
        await sortStaticList(saleOrder.line_ids);

        if (hasOptionalProducts && !edit) {
            const selectedComboProducts = selectedComboItems.map((item) => ({
                name: item.product.display_name,
            }));
            await this._openProductConfigurator(false, selectedComboProducts);
        }
    }

    /** @return {Object} */
    _getAdditionalRpcParams() {
        return {};
    }

    /** @return {Object} */
    _getAdditionalDialogProps() {
        const isOptionalLine = this.env.shouldCollapse(
            this.props.record,
            "is_optional",
        );
        return {
            options: {
                showQuantity: !isOptionalLine,
                showPrice: !isOptionalLine,
            },
        };
    }

    _prepareNewLineData(line, product) {
        if (this.env.shouldCollapse(line, "is_optional")) {
            return { ...product, quantity: 0 };
        }
        return product;
    }

    /** @return {Number[]} */
    _getVariantPtavIds(saleOrderLine) {
        return saleOrderLine.product_template_attribute_value_ids.currentIds;
    }

    /** @return {Number[]} */
    _getNoVariantPtavIds(saleOrderLine) {
        return saleOrderLine.product_no_variant_attribute_value_ids.currentIds;
    }

    /** @return {Promise<CustomPtav[]>} */
    async _getCustomPtavs(saleOrderLine) {
        const customPtavIds = saleOrderLine.product_custom_attribute_value_ids;
        let customPtavs = [];
        if (customPtavIds.records[0]?.isNew) {
            customPtavs = customPtavIds.records.map((record) => record.data);
        } else if (customPtavIds.currentIds.length) {
            const specification = {
                custom_product_template_attribute_value_id: {
                    fields: { id: {} },
                },
                custom_value: {},
            };
            customPtavs = await this.orm.webRead(
                "product.attribute.custom.value",
                customPtavIds.currentIds,
                { specification },
            );
        }
        return customPtavs.map((customPtav) => ({
            id:
                customPtav.custom_product_template_attribute_value_id &&
                customPtav.custom_product_template_attribute_value_id.id,
            value: customPtav.custom_value,
        }));
    }
}

export const saleOrderLineProductField = {
    ...productLabelSectionAndNoteField,
    component: SaleOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            ...productLabelSectionAndNoteField.extractProps(fieldInfo, dynamicInfo),
            readonlyField: dynamicInfo.readonly,
        };
    },
    fieldDependencies: [
        { name: "is_configurable_product", type: "boolean" },
        { name: "product_type", type: "selection" },
        { name: "product_template_attribute_value_ids", type: "many2many" },
        { name: "product_name_translated", type: "char" },
    ],
};

registry.category("fields").add("sol_product_many2one", saleOrderLineProductField);
