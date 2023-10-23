/** @odoo-module **/

import { x2ManyCommands } from "@web/core/orm_service";
import { useService } from "@web/core/utils/hooks";
import { ProductConfiguratorDialog } from "@product/js/product_configurator/product_configurator_dialog/product_configurator_dialog";
import { _t } from "@web/core/l10n/translation";
import { useEffect } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";

export async function applyProduct(record, quantityFieldName, product) {
    // handle custom values & no variants
    const contextRecords = [];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = ptal.attribute_values.find(
            ptav => ptav.is_custom && ptal.selected_attribute_value_ids.includes(ptav.id)
        );
        if (selectedCustomPTAV) {
            contextRecords.push({
                default_custom_product_template_attribute_value_id: selectedCustomPTAV.id,
                default_custom_value: ptal.customValue,
                res_model: record.model.config.resModel,
            });
        };
    }

    const proms = [];
    proms.push(record.data.product_custom_attribute_value_ids.createAndReplace(contextRecords));

    const noVariantPTAVIds = product.attribute_lines.filter(
        ptal => ptal.create_variant === "no_variant" && ptal.attribute_values.length > 1
    ).flatMap(ptal => ptal.selected_attribute_value_ids);

    await Promise.all(proms);

    let fieldsToUpdate = {
        product_id: [product.id, product.display_name],
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
    };

    if(quantityFieldName){
        fieldsToUpdate[quantityFieldName] = product.quantity;
    }

    await record.update(fieldsToUpdate);
}

export class ProductField extends Many2OneField {
    static template = "product.product_configurator.productField";
    static props = {
        ...Many2OneField.props,
        productTemplateFieldName: String,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        let isMounted = false;
        let isInternalUpdate = false;
        this.dialog = useService("dialog");
        this.orm = useService("orm");
        const { updateRecord } = this;
        this.updateRecord = (value) => {
            isInternalUpdate = true;
            return updateRecord.call(this, value);
        };
        useEffect(value => {
            if (!isMounted) {
                isMounted = true;
            } else if (value && isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
                if (this.relation === "product.template") {
                    this._onProductTemplateUpdate();
                }
            }
            isInternalUpdate = false;
        }, () => [Array.isArray(this.value) && this.value[0]]);
    }

    get isProductClickable() {
        return this.props.readonlyField;
    }

    get hasExternalButton() {
        // Keep external button, even if field is specified as 'no_open' so that the user is not
        // redirected to the product when clicking on the field content
        const res = super.hasExternalButton;
        return res || (!!this.props.record.data[this.props.name] && !this.state.isFloating);
    }

    get hasConfigurationButton() {
        return this.isConfigurableTemplate;
    }

    get isConfigurableTemplate() {
        return super.isConfigurableTemplate || this.props.record.data.is_configurable_product;
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }

    get productConfiguratorDialogComponent() {
        return ProductConfiguratorDialog;
    }

    get quantityFieldName() {
        return 'product_uom_qty';
    }

    get productTemplateFieldName() {
        return this.props.productTemplateFieldName;
    }

    get productUomFieldName() {
        return 'product_uom_id';
    }

    get options() {
        return {
            showQty: true,
        };
    }

    async _onProductTemplateUpdate() {
        const result = await this.orm.call(
            'product.template',
            'get_single_product_variant',
            [this.props.record.data[this.productTemplateFieldName][0]],
            {
                context: this.context,
            }
        );
        if(result && result.product_id) {
            if (this.props.record.data.product_id != result.product_id.id) {
                if (result.has_optional_products) {
                    this._openProductConfigurator();
                } else {
                    await this.props.record.update({
                        product_id: [result.product_id, result.product_name],
                    });
                    this._onProductUpdate?.();  // sale
                }
            }
        } else {
            await this._openConfigurator(result)
        }
    }

    onEditConfiguration() {
        this._editProductConfiguration();
    }

    _editProductConfiguration() { //TODO VCR
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator(true);
        }
    }

    /**
     * Open the configurator. By default, open the product configurator.
     *
     * For a module to open a different configurator, it must override this method.
     *
     * @param {Object} result - values provided by `product_template.get_single_product_variant`
     */
    async _openConfigurator(result) {
        this._openProductConfigurator();
    }

    async _openProductConfigurator(edit=false) {
        this.dialog.add(
            this.productConfiguratorDialogComponent,
            await this.getProductConfiguratorDialogProps(edit, this.options),
        );
    }

    async getProductConfiguratorDialogProps(edit, options) {
        let ptavIds = this.props.record.data.product_template_attribute_value_ids.records.map(
            record => record.resId
        );
        let customAttributeValues = [];

        if (edit) {
            /**
             * no_variant and custom attribute don't need to be given to the configurator for new
             * products.
             */
            ptavIds = ptavIds.concat(
                this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                    record => record.resId
                )
            );
            /**
             * `product_custom_attribute_value_ids` records are not loaded in the view bc sub
             * templates are not loaded in list views. Therefore, we fetch them from the server if
             * the record is saved. Else we use the value stored on the line.
             */
            customAttributeValues =
                this.props.record.data.product_custom_attribute_value_ids.records[0]?.isNew ?
                this.props.record.data.product_custom_attribute_value_ids.records.map(
                    record => record.data
                ) :
                await this.orm.read(
                    'product.attribute.custom.value',
                    this.props.record.data.product_custom_attribute_value_ids.currentIds,
                    ["custom_product_template_attribute_value_id", "custom_value"]
                )
        }
        let productConfiguratorDialogProps = {
            productTemplateId: this.props.record.data[this.productTemplateFieldName][0],
            ptavIds: ptavIds,
            customAttributeValues: customAttributeValues.map(
                data => {
                    return {
                        ptavId: data.custom_product_template_attribute_value_id[0],
                        value: data.custom_value,
                    }
                }
            ),
            model: this.props.record.model.config.resModel,
            companyId: this.props.record.model.root.data.company_id[0],
            edit: edit,
            options: {
                showQty: options.showQty,
            },
            save: this.saveProductConfiguratorDialog.bind(this),
            discard: this.discardProductConfiguratorDialog.bind(this),
        }

        if (options.showQty){
            Object.assign(productConfiguratorDialogProps, {
                quantity: this.props.record.data[this.quantityFieldName],
                productUOMId: this.props.record.data[this.productUomFieldName][0],
            })
        }

        return productConfiguratorDialogProps;
    }

    async saveProductConfiguratorDialog(mainProduct) {
        await applyProduct(this.props.record, this.quantityFieldName, mainProduct);
    }

    async discardProductConfiguratorDialog() {}
}

export const productField = {
    ...many2OneField,
    component: ProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.productTemplateFieldName = fieldInfo.name;
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category("fields").add("product_many2one", productField);
