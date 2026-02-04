/** @odoo-module */

import { SaleOrderLineProductField } from '@sale/js/sale_product_field';
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { useService } from "@web/core/utils/hooks";
import { patch } from "@web/core/utils/patch";
import { ProductConfiguratorDialog } from "./product_configurator_dialog/product_configurator_dialog";

async function applyProduct(record, product) {
    // handle custom values & no variants
    const customAttributesCommands = [
        x2ManyCommands.set([]),  // Command.clear isn't supported in static_list/_applyCommands
    ];
    for (const ptal of product.attribute_lines) {
        const selectedCustomPTAV = ptal.attribute_values.find(
            ptav => ptav.is_custom && ptal.selected_attribute_value_ids.includes(ptav.id)
        );
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

    await record.update({
        product_id: [product.id, product.display_name],
        product_uom_qty: product.quantity,
        product_no_variant_attribute_value_ids: [x2ManyCommands.set(noVariantPTAVIds)],
        product_custom_attribute_value_ids: customAttributesCommands,
    });
};

patch(SaleOrderLineProductField.prototype, {

    setup() {
        super.setup(...arguments);

        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm");
    },

    async _onProductTemplateUpdate() {
        super._onProductTemplateUpdate(...arguments);
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
                if (result.has_optional_products) {
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
    },

    _editProductConfiguration() {
        super._editProductConfiguration(...arguments);
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator(true);
        }
    },

    get isConfigurableTemplate() {
        return super.isConfigurableTemplate || this.props.record.data.is_configurable_product;
    },

    async getProductConfiguratorDialogProps(edit=false) {
        const saleOrderRecord = this.props.record.model.root;
        let ptavIds = this.props.record.data.product_template_attribute_value_ids.records.map(
            record => record.resId
        );
        let customAttributeValues = [];

        if (edit) {
            /**
             * no_variant and custom attribute don't need to be given to the configurator for new
             * products.
             */
            ptavIds = ptavIds.concat(this.props.record.data.product_no_variant_attribute_value_ids.records.map(
                record => record.resId
            ));
            /**
             *  `product_custom_attribute_value_ids` records are not loaded in the view bc sub templates
             *  are not loaded in list views. Therefore, we fetch them from the server if the record is
             *  saved. Else we use the value stored on the line.
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

        return {
            productTemplateId: this.props.record.data.product_template_id[0],
            ptavIds: ptavIds,
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
        }
    },

    async _openProductConfigurator(edit=false) {
        const productConfiguratorDialogProps = await this.getProductConfiguratorDialogProps(edit);
        return this.dialog.add(ProductConfiguratorDialog, productConfiguratorDialogProps);
    },
});
