import {
    accountProductField,
    AccountProductField,
} from "@account/components/account_product_field/account_product_field";
import { useEffect } from "@odoo/owl";
import { saleProductMixin } from "@sale/js/sale_product_mixin";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";

export class SaleOrderTemplateLineProductField extends AccountProductField {
    static template = "sale.SaleProductField";

    setup() {
        super.setup();
        this.isInternalUpdate = false;
        let isMounted = false;

        useEffect(() => {
            const value = this.value && this.value.id;
            if (!isMounted) {
                isMounted = true;
            } else if (value && this.isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external
                // source, such as an onchange, or the product configuration dialog itself
                if (this.relation === "product.template") {
                    this._onProductTemplateUpdate();
                } else {
                    this._onProductUpdate();
                }
            }
            this.isInternalUpdate = false;
        });
    }

    get productName() {
        if (this.props.name == "product_template_id") {
            const product_id_data = this.props.record.data.product_id;
            if (product_id_data && product_id_data.display_name) {
                return product_id_data.display_name.split("\n")[0];
            }
        }
        return this.props.record.data[this.props.name].display_name;
    }

    // Hooks for saleProductMixin
    _onProductTemplateUpdate() {}
    _onProductUpdate() {}
    onEditConfiguration() {}

    get isProductClickable() {
        return false;
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    get m2oProps() {
        const props = super.m2oProps;
        let value = props.value && { ...props.value };
        if (this.props.readonly && this.productName) {
            value = { ...value, display_name: this.productName };
        }
        return {
            ...props,
            update: (value) => {
                this.isInternalUpdate = true;
                return props.update(value);
            },
            value,
        };
    }
}

// for enabling configurators
patch(SaleOrderTemplateLineProductField.prototype, saleProductMixin());

// `saleProductMixin` defines its own `_getOrderLines`/`_getSoDate`/`_getAdditionalDialogProps`/
// `_getAdditionalRpcParams`/`_useGridConfigurator`/`_prepareNewLineData` without calling
// `super.X()`, so patching it above would silently discard class-body overrides of those same
// names. Patching them separately, after the mixin, makes ours the active version (with the
// mixin's own version reachable as their `super()` fallback).
patch(SaleOrderTemplateLineProductField.prototype, {
    _getOrderLines() {
        return this.props.record.model.root.data.sale_order_template_line_ids;
    },

    _getSoDate() {
        return serializeDateTime(today());
    },

    _getAdditionalDialogProps() {
        const props = super._getAdditionalDialogProps();
        const isOptionalLine = this.env.shouldCollapse(this.props.record, "is_optional");
        // A quotation template has no customer/company context, so prices are
        // not relevant here (and the currency would be ambiguous for templates
        // shared across companies). Hide prices in the configurator.
        props.options = { ...props.options, showQuantity: !isOptionalLine, showPrice: false };
        return props;
    },

    _prepareNewLineData(line, product) {
        const data = super._prepareNewLineData(line, product);
        if (this.env.shouldCollapse(line, "is_optional")) {
            data.quantity = 0;
        }
        return data;
    },

    _getAdditionalRpcParams() {
        // Prices are hidden in the configurator for templates (see `_getAdditionalDialogProps`),
        // so skip server-side price computation entirely.
        return { ...super._getAdditionalRpcParams(), show_price: false };
    },

    _useGridConfigurator() {
        // Quotation template lines don't support the grid/matrix product selector.
        return false;
    },
});

export const saleOrderTemplateProductField = {
    ...accountProductField,
    component: SaleOrderTemplateLineProductField,
    fieldDependencies: [
        { name: "product_id", type: "many2one" },
        { name: "product_uom_id", type: "many2one" },
        { name: "product_uom_qty", type: "float" },
        { name: "is_configurable_product", type: "boolean" },
        { name: "product_template_attribute_value_ids", type: "many2many" },
    ],
};

registry.category("fields").add("sotl_product_many2one", saleOrderTemplateProductField);
