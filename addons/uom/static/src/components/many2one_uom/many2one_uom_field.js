import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import {
    buildM2OFieldDescription,
    extractM2OFieldProps,
    m2oSupportedOptions,
    Many2OneField,
} from "@web/views/fields/many2one/many2one_field";
import { getProductRelatedModel, Many2XUomTagsAutocomplete } from "../many2x_uom_tags/many2x_uom_tags";

// @todo: this extension will be removed in the future
// when the autocomplete source generation come from a hook.
class UomMany2One extends Many2One {
    static components = {
        ...super.components,
        Many2XAutocomplete: Many2XUomTagsAutocomplete,
    };
    static props = {
        ...super.props,
        productModel: { type: String, optional: true },
        productId: { type: Number, optional: true },
        productQuantity: { type: Number, optional: true },
    };

    get many2XAutocompleteProps() {
        return {
            ...super.many2XAutocompleteProps,
            productModel: this.props.productModel,
            productId: this.props.productId,
            productQuantity: this.props.productQuantity,
        };
    }
}

export class Many2OneUomField extends Component {
    static template = "uom.Many2OneUomField";
    static components = { UomMany2One };
    static props = {
        ...Many2OneField.props,
        productField: { type: String, optional: true },
        quantityField: { type: String, optional: true },
    };
    static defaultProps = {
        ...Many2OneField.defaultProps,
        productField: "product_id",
        quantityField: "product_uom_qty",
    };

    get m2oProps() {
        const productModel = getProductRelatedModel.call(this);
        let productId = this.props.record.data[this.props.productField]?.id || 0;
        if (["product.template", "product.product"].includes(this.props.record.resModel)) {
            productId = this.props.record.resId || 0;
        }
        return {
            ...computeM2OProps(this.props),
            productModel,
            productId,
            productQuantity: this.props.record.data[this.props.quantityField],
            // specification: {
            //     name: {},
            //     relative_factor: {},
            //     relative_uom_id: {
            //         fields: {
            //             display_name: {},
            //         },
            //     },
            // },
        };
    }

    getLabel(record) {
        return record.name ? record.name.split("\n")[0] : _t("Unnamed");
    }
}

registry.category("fields").add("many2one_uom", {
    ...buildM2OFieldDescription(Many2OneUomField),
    additionalClasses: ["o_field_many2one"],
    extractProps(staticInfo, dynamicInfo) {
        return {
            ...extractM2OFieldProps(staticInfo, dynamicInfo),
            productField: staticInfo.options.product_field,
            quantityField: staticInfo.options.quantity_field,
        };
    },
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Product Field Name"),
            name: "product_field",
            type: "field",
            availableTypes: ["many2one"],
        },
        {
            label: _t("Quantity Field Name"),
            name: "quantity_field",
            type: "field",
            availableTypes: ["many2one"],
        },
    ],
});
