/** @odoo-module **/

import { useEffect } from '@odoo/owl';
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { serializeDateTime } from "@web/core/l10n/dates";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog";

async function applyProduct(record, product) {
    // handle custom values & no variants
    const contextRecords = [];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = ptal.attribute_values.find(
            ptav => ptav.is_custom && ptav.id === ptal.selected_attribute_value_id
        );
        if (selectedCustomPTAV) {
            contextRecords.push({
                default_custom_product_template_attribute_value_id: selectedCustomPTAV.id,
                default_custom_value: ptal.customValue,
            });
        };
    }

    const proms = [];
    proms.push(record.data.product_custom_attribute_value_ids.createAndReplace(contextRecords));

    const noVariantPTAVIds = product.attribute_lines.filter(
        ptal => ptal.create_variant === "no_variant" && ptal.attribute_values.length > 1
    ).map(ptal => ptal.selected_attribute_value_id);

    await Promise.all(proms);
    await record.update({
        product_id: [product.id, product.display_name],
        product_no_variant_attribute_value_ids: noVariantPTAVIds,
    });
    // TODO
    await record.update({
        product_qty: product.quantity,
    });
};

export class PurchaseOrderLineProductField extends Many2OneField {
    static props = {
        ...Many2OneField.props,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        let isMounted = false;
        let isInternalUpdate = false;
        const { updateRecord } = this;
        this.updateRecord = (value) => {
            isInternalUpdate = true;
            return updateRecord.call(this, value);
        };
        useEffect(value => {
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                if (this.relation === "product.template") {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

    get isProductClickable() {
        return (
            this.props.readonlyField ||
            (this.props.record.model.root.activeFields.order_line &&
                this.props.record.model.root._isReadonly("order_line"))
        );
    }
    get hasExternalButton() {
        const res = super.hasExternalButton;
        return res || (!!this.props.record.data[this.props.name] && !this.state.isFloating);
    }
    get hasConfigurationButton() {
        return this.isConfigurableLine || this.isPurchaseConfigurableTemplate;
    }
    get isConfigurableLine() {
        return false;
    }
    get isConfigurableTemplate() {
        return false;
    }

    get configurationButtonHelp() {
        return this.env._t("Edit Configuration");
    }

    get configurationButtonIcon() {
        return "btn btn-secondary fa " + this.configurationButtonFAIcon();
    }

    configurationButtonFAIcon() {
        return "fa-pencil";
    }

    onClick(ev) {
        if (this.props.readonly) {
            ev.stopPropagation();
            this.openAction();
        } else {
            super.onClick(ev);
        }
    }

    async _onProductTemplateUpdate() {
        const context = this.context;
        context['from_purchase'] = true;
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data.product_template_id[0]],
            { context: context}
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                await this.props.record.update({
                    product_id: [result.product_id, result.product_name],
                });
                if (result.is_configurable_product) {
                    this._openProductConfigurator();
                } else {
                    this._onProductUpdate();
                }
            }
        } else {
            if (!result.mode || result.mode === 'configurator_purchase') {
                this._openProductConfigurator(false);
            } else {
                // only triggered when purchase_product_matrix is installed.
                this._openGridConfigurator(false);
            }
        }
    }

    async _onProductUpdate() {}

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            this._editProductConfiguration();
        }
    }
    _editLineConfiguration() {}

    _editProductConfiguration() {
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator(true);
        }
    }

    get isPurchaseConfigurableTemplate() {
        return this.props.record.data.is_configurable_product || this.isConfigurableTemplate;
    }

    async _openProductConfigurator(edit=false) {
        const purchaseOrderRecord = this.props.record.model.root;

        /**
         *  `product_custom_attribute_value_ids` records are not loaded in the view because sub templates
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
                record => record.resId
            ).concat(this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                record => record.resId
            )),
            customAttributeValues: customAttributeValues.map(
                data => {
                    return {
                        ptavId: data.custom_product_template_attribute_value_id[0],
                        value: data.custom_value,
                    }
                }
            ),
            quantity: this.props.record.data.product_qty || 1,
            productUOMId: this.props.record.data.product_uom[0],
            companyId: purchaseOrderRecord.data.company_id[0],
            partnerId: purchaseOrderRecord.data.partner_id[0],
            currencyId: this.props.record.data.currency_id[0],
            poDate: serializeDateTime(purchaseOrderRecord.data.date_order),
            edit: edit,
            save: async (mainProduct) => {
                await applyProduct(this.props.record, mainProduct);
                this._onProductUpdate();
                purchaseOrderRecord.data.order_line.leaveEditMode();
            },
            discard: () => {
                purchaseOrderRecord.data.order_line.delete(this.props.record);
            },
        });
    }
}

PurchaseOrderLineProductField.template = "purchase_product_configurator.PurchaseProductField";

export const purchaseOrderLineProductField = {
    ...many2OneField,
    component: PurchaseOrderLineProductField,
    extractProps(dynamicInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category("fields").add("pol_product_many2one", purchaseOrderLineProductField);
