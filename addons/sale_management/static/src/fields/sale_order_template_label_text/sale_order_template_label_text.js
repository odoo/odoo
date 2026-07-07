import {
    AccountLabelTextField,
    listAccountLabelText,
} from "@account/components/account_label_text/account_label_text";
import { Component, useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { textField, ListTextField } from "@web/views/fields/text/text_field";
import { serializeDateTime, today } from "@web/core/l10n/dates";
import { saleProductMixin } from "@sale/js/sale_product_mixin";

export class SaleOrderTemplateLabelTextField extends AccountLabelTextField {
    static template = "sale.SaleLabelTextField";

    get m2XAutoCompleteModel() {
        return "product.template";
    }

    get productDomain() {
        return [["sale_ok", "=", true]];
    }

    get canEditProduct() {
        return (
            super.canEditProduct &&
            !this.props.record.data.mandatory_product &&
            (this.props.record.data.state != "sale" || this.props.record.isNew)
        );
    }

    get product() {
        return this.props.record.data.product_template_id;
    }

    async updateMany2XProduct(record) {
        await this.props.record.update({ product_template_id: { id: record.id } });
        if (!this.props.record.data.product_template_id) {
            return;
        }
        // The label autocomplete is not bound to the product field itself, so run the
        // product configuration flow after the template update has been applied.
        void this._onProductTemplateUpdate();
    }

    // Hooks for saleProductMixin
    get isCombo() {
        return false;
    }
    get hasConfigurationButton() {
        return false;
    }
    get configurationButtonHelp() {
        return "";
    }
    get isConfigurableTemplate() {
        return false;
    }
    _onProductTemplateUpdate() {}
    onEditConfiguration() {}
}

// for enabling configurators and combos
patch(SaleOrderTemplateLabelTextField.prototype, saleProductMixin());

// `saleProductMixin` defines its own `_getOrderLines`/`_getSoDate`/`_getAdditionalDialogProps`/
// `_getAdditionalRpcParams`/`_useGridConfigurator`/`_prepareNewLineData` without calling
// `super.X()`, so patching it above would silently discard class-body overrides of those same
// names. Patching them separately, after the mixin, makes ours the active version (with the
// mixin's own version reachable as their `super()` fallback).
patch(SaleOrderTemplateLabelTextField.prototype, {
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

export class ListSaleOrderTemplateLineLabelTextField extends Component {
    static template = "sale.ListSaleOrderLineLabelTextField";
    props = useProps({
        ...standardFieldProps,
        context: t.object().optional(),
    });

    get componentToUse() {
        const record = this.props.record;
        if (!record.data.display_type && "product_id" in record.activeFields) {
            return SaleOrderTemplateLabelTextField;
        }
        return ListTextField;
    }

    get componentProps() {
        if (this.componentToUse === SaleOrderTemplateLabelTextField) {
            return this.props;
        }
        return omit(this.props, "context");
    }
}

export const listSaleOrderTemplateLineLabelText = {
    ...listAccountLabelText,
    component: ListSaleOrderTemplateLineLabelTextField,
    fieldDependencies: [
        { name: "product_id", type: "many2one" },
        { name: "product_uom_id", type: "many2one" },
        { name: "product_uom_qty", type: "float" },
        { name: "is_configurable_product", type: "boolean" },
        { name: "product_template_attribute_value_ids", type: "many2many" },
    ],
};

registry.category("fields").add("sotl_label_text", textField);
registry.category("fields").add("list.sotl_label_text", listSaleOrderTemplateLineLabelText);
