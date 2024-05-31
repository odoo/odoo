/** @odoo-module **/

import { registry } from "@web/core/registry";
import { productField, ProductField, applyProduct } from "@product/js/product_configurator/product_configurator_field";
import { SaleProductConfiguratorDialog } from "@sale/js/product_configurator_dialog/product_configurator_dialog";
import { serializeDateTime } from "@web/core/l10n/dates";

export class SaleOrderLineProductField extends ProductField {

    get isProductClickable() {
        // product form should be accessible if the widget field is readonly
        // or if the line cannot be edited (e.g. locked SO)
        return super.isProductClickable || (
            this.props.record.model.root.activeFields.order_line &&
            this.props.record.model.root._isReadonly("order_line")
        );
    }

    get hasConfigurationButton() {
        return this.isConfigurableLine || super.hasConfigurationButton;
    }

    get isConfigurableLine() {
        return false;
    }

    get productConfiguratorDialogComponent() {
        if (this.props.record.model.config.resModel === 'sale.order') {
            return SaleProductConfiguratorDialog;
        } else {
            super.productConfiguratorDialogComponent;
        }
    }

    get productUomFieldName() {
        if (this.props.record.model.config.resModel === 'sale.order') {
            return 'product_uom';
        } else {
            return super.productUomFieldName;
        }
    }

    get productTemplateFieldName() {
        if (this.props.record.model.config.resModel === 'sale.order') {
            return 'product_template_id';
        } else {
            return super.productTemplateFieldName;
        }
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

    async _onProductUpdate() {} // event_booth_sale, event_sale, sale_renting

    onEditConfiguration() {
        if (this.isConfigurableLine) {
            this._editLineConfiguration();
        } else {
            super._editProductConfiguration();
        }
    }

    _editLineConfiguration() {} // event_booth_sale, event_sale, sale_renting

    _editProductConfiguration() { // sale_product_matrix
        if (this.props.record.data.is_configurable_product) {
            this._openProductConfigurator(true);
        }
    }

    /**
     * Override of `product` to open the grid configurator if requested.
     *
     * @param {Object} result - values provided by `product_template.get_single_product_variant`
     */
    async _openConfigurator(result) {
        if (result.mode && result.mode === 'matrix') {
            // only triggered when sale_product_matrix is installed.
            this._openGridConfigurator();
        } else {
            super._openConfigurator();
        }
    }

    async getProductConfiguratorDialogProps() {
        const saleOrderRecord = this.props.record.model.root;
        let productConfiguratorDialogProps = await super.getProductConfiguratorDialogProps(
            ...arguments
        );
        Object.assign(productConfiguratorDialogProps, {
            pricelistId: saleOrderRecord.data.pricelist_id[0],
            currencyId: saleOrderRecord.data.currency_id[0],
            soDate: serializeDateTime(saleOrderRecord.data.date_order),
        })
        return productConfiguratorDialogProps;
    }

    async saveProductConfiguratorDialog(mainProduct, optionalProducts) {
        await super.saveProductConfiguratorDialog(...arguments);

        this._onProductUpdate();
        const saleOrderRecord = this.props.record.model.root;
        saleOrderRecord.data.order_line.leaveEditMode();
        for (const optionalProduct of optionalProducts) {
            const line = await saleOrderRecord.data.order_line.addNewRecord({
                position: 'bottom',
                mode: "readonly",
            });
            await applyProduct(line, this.quantityFieldName, optionalProduct);
        }
    }

    async discardProductConfiguratorDialog() {
        super.discardProductConfiguratorDialog(...arguments);
        const saleOrderRecord = this.props.record.model.root;
        saleOrderRecord.data.order_line.delete(this.props.record);
    }
}

export const saleOrderLineProductField = {
    ...productField,
    component: SaleOrderLineProductField,
};

registry.category("fields").add("sol_product_many2one", saleOrderLineProductField);
