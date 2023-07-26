/** @odoo-module */

import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
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
        product_uom_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.replaceWith(noVariantPTAVIds)],
    });
};

patch(SaleOrderLineProductField.prototype, 'sale_product_configurator', {

    setup() {
        this._super(...arguments);

        this.dialog = useService("dialog");
        this.orm = useService("orm");
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
            quantity: this.props.record.data.product_uom_qty,
            productUOMId: this.props.record.data.product_uom[0],
            companyId: saleOrderRecord.data.company_id[0],
            pricelistId: saleOrderRecord.data.pricelist_id[0],
            currencyId: this.props.record.data.currency_id[0],
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
            edit: edit,
            save: async (mainProduct, optionalProducts) => {
                await applyProduct(this.props.record, mainProduct);

                this._onProductUpdate();
                saleOrderRecord.data.order_line.leaveEditMode();
                for (const optionalProduct of optionalProducts) {
                    const line = await saleOrderRecord.data.order_line.addNewRecord({
                        position: 'bottom',
                        mode: "readonly",
                    });
                    await applyProduct(line, optionalProduct);
                }
            },
            discard: () => {
                saleOrderRecord.data.order_line.delete(this.props.record);
            },
        });
    },
});
