import {
    AccountLabelTextField,
    listAccountLabelText,
} from "@account/components/account_label_text/account_label_text";
import { Component, useProps, t } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { omit } from "@web/core/utils/objects";
import { patch } from "@web/core/utils/patch";
import { CharField } from "@web/views/fields/char/char_field";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { TextField, ListTextField } from "@web/views/fields/text/text_field";
import { saleProductMixin } from "../sale_product_mixin";

export class SaleLabelTextField extends AccountLabelTextField {
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
            !this.props.record.data.combo_item_id &&
            (this.props.record.data.state != "sale" || this.props.record.isNew)
        );
    }

    get product() {
        return this.props.record.data.product_template_id;
    }

    async updateMany2XProduct(record) {
        const wasCombo = this.isCombo;
        const updateValues = { product_template_id: { id: record.id } };
        if (wasCombo) {
            updateValues.selected_combo_items = "[]";
        }
        await this.props.record.update(updateValues);
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
patch(SaleLabelTextField.prototype, saleProductMixin());

export class SaleOrderLineLabelTextField extends Component {
    static template = "sale.SaleOrderLineLabelTextField";
    props = useProps(standardFieldProps);

    get componentToUse() {
        return this.props.record.data.product_type === "combo" ? CharField : TextField;
    }
}

export class ListSaleOrderLineLabelTextField extends Component {
    static template = "sale.ListSaleOrderLineLabelTextField";
    props = useProps({
        ...standardFieldProps,
        context: t.object().optional(),
    });

    get componentToUse() {
        const record = this.props.record;
        if (!record.data.display_type && "product_id" in record.activeFields) {
            return SaleLabelTextField;
        } else if (record.data.product_type === "combo") {
            return CharField;
        }
        return ListTextField;
    }

    get componentProps() {
        if (this.componentToUse === SaleLabelTextField) {
            return this.props;
        }
        return omit(this.props, "context");
    }
}

export const saleOrderLineLabelText = {
    component: SaleOrderLineLabelTextField,
};

export const listSaleOrderLineLabelText = {
    ...listAccountLabelText,
    component: ListSaleOrderLineLabelTextField,
    fieldDependencies: [
        { name: "is_configurable_product", type: "boolean" },
        { name: "product_type", type: "selection" },
        { name: "service_tracking", type: "selection" },
        { name: "product_template_attribute_value_ids", type: "many2many" },
        { name: "mandatory_product", type: "boolean" },
    ],
};

registry.category("fields").add("sol_label_text", saleOrderLineLabelText);
registry.category("fields").add("list.sol_label_text", listSaleOrderLineLabelText);
