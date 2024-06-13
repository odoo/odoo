/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useEffect } from '@odoo/owl';
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { serializeDateTime } from "@web/core/l10n/dates";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
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


export class SaleOrderLineProductField extends Many2OneField {
    static template = "sale.SaleProductField";
    static props = {
        ...Many2OneField.props,
        readonlyField: { type: Boolean, optional: true },
    };

    setup() {
        super.setup();
        this.dialog = useService("dialog");
        this.notification = useService("notification");
        this.orm = useService("orm")
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
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
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
        return this.isConfigurableLine || this.isConfigurableTemplate;
    }
    get isConfigurableLine() {
        return false;
    }
    get isConfigurableTemplate() {
        return this.props.record.data.is_configurable_product;
    }

    get configurationButtonHelp() {
        return _t("Edit Configuration");
    }

    get configurationButtonIcon() {
        return "btn btn-secondary fa " + this.configurationButtonFAIcon();
    }

    configurationButtonFAIcon() {
        return "fa-pencil";
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
    }

    async _onProductUpdate() {} // event_booth_sale, event_sale, sale_renting

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            this._editProductConfiguration();
        }
    }
    _editLineConfiguration() {} // event_booth_sale, event_sale, sale_renting
    _editProductConfiguration() { // sale_product_matrix
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator(true);
        }
    }

    async _openProductConfigurator(edit=false) {
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

        this.dialog.add(ProductConfiguratorDialog, {
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
        });
    }
}

export const saleOrderLineProductField = {
    ...many2OneField,
    component: SaleOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        const props = many2OneField.extractProps(...arguments);
        props.readonlyField = dynamicInfo.readonly;
        return props;
    },
};

registry.category("fields").add("sol_product_many2one", saleOrderLineProductField);
