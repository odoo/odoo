import { t, useEffect, useProps } from "@odoo/owl";
import {
    ProductLabelSectionAndNoteField,
    productLabelSectionAndNoteField,
    productLabelSectionAndNoteFieldProps,
} from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";
import { registry } from "@web/core/registry";
import { patch } from "@web/core/utils/patch";
import { Many2One, many2OneProps } from "@web/views/fields/many2one/many2one";
import { Many2XAutocomplete, many2XAutocompleteProps } from "@web/views/fields/relational_utils";
import { saleProductMixin } from "../sale_product_mixin";

class ProductSearchMany2XAutocomplete extends Many2XAutocomplete {
    props = useProps({ ...many2XAutocompleteProps, onProductSearch: t.function().optional() });

    /**
     * @override
     */
    search(name, domain, context) {
        this.props.onProductSearch?.(name);
        return super.search(name, domain, context);
    }

    /**
     * @override
     */
    onSearchMore(request) {
        this.props.onProductSearch?.("");
        return super.onSearchMore(request);
    }
}

class ProductSearchMany2One extends Many2One {
    static components = {
        ...Many2One.components,
        Many2XAutocomplete: ProductSearchMany2XAutocomplete,
    };
    props = useProps({ ...many2OneProps, onProductSearch: t.function().optional() });

    /**
     * @override
     */
    get many2XAutocompleteProps() {
        return { ...super.many2XAutocompleteProps, onProductSearch: this.props.onProductSearch };
    }
}

export class SaleOrderLineProductField extends ProductLabelSectionAndNoteField {
    static template = "sale.SaleProductField";
    static components = { Many2One: ProductSearchMany2One };
    props = useProps({
        ...productLabelSectionAndNoteFieldProps,
        readonlyField: t.boolean().optional(),
    });

    setup() {
        super.setup();
        this.isInternalUpdate = false;
        this.wasCombo = false;
        this.lastProductSearch = "";
        let isMounted = false;

        useEffect(() => {
            const value = this.value && this.value.id;
            if (!isMounted) {
                isMounted = true;
            } else if (value && this.isInternalUpdate) {
                // we don't want to trigger product update when update comes from an external sources,
                // such as an onchange, or the product configuration dialog itself
                if (this.wasCombo) {
                    // If the previously selected product was a combo, delete its selected combo
                    // items before changing the product.
                    this.props.record.update({ selected_combo_items: "[]" });
                }
                if (this.relation === "product.template" || this.isCombo) {
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
        return super.productName;
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

    get isDownpayment() {
        return this.props.record.data.is_downpayment;
    }

    get label() {
        let label = this.props.record.data.name;
        if (this.translatedProductName && label.startsWith(this.translatedProductName)) {
            // Remove the translated name as it is already shown to the salesman on the SOL.
            label = label.slice(this.translatedProductName.length + 1); // + "\n"
        } else {
            label = super.label;
        }
        return label;
    }

    get translatedProductName() {
        return this.props.record.data.translated_product_name;
    }

    get m2oProps() {
        const props = super.m2oProps;
        return {
            ...props,
            canOpen: this.props.canOpen && (!this.props.readonly || this.isProductClickable),
            onProductSearch: (name) => {
                this.lastProductSearch = name;
            },
            update: (value) => {
                this.isInternalUpdate = true;
                this.wasCombo = this.isCombo;
                return props.update(value);
            },
        };
    }

    get relation() {
        return this.props.record.fields[this.props.name].relation;
    }

    get value() {
        return this.props.record.data[this.props.name];
    }

    /**
     * @override
     */
    shouldShowWarning() {
        return super.shouldShowWarning() && !this.isDownpayment;
    }

    parseLabel(value) {
        if (!this.translatedProductName) {
            return super.parseLabel(value);
        }
        return (
            (value && this.translatedProductName.concat("\n", value)) || this.translatedProductName
        );
    }

    // Hooks for saleProductMixin
    get isCombo() {
        return false;
    }
    get hasConfigurationButton() {
        return false;
    }
    get isConfigurableTemplate() {
        return false;
    }
    get configurationButtonHelp() {
        return "";
    }
    _onProductTemplateUpdate() {}
    _onProductUpdate() {}
    onEditConfiguration() {}
}

// for enabling configurators and combos
patch(SaleOrderLineProductField.prototype, saleProductMixin());

export const saleOrderLineProductField = {
    ...productLabelSectionAndNoteField,
    component: SaleOrderLineProductField,
    extractProps(fieldInfo, dynamicInfo) {
        return {
            ...productLabelSectionAndNoteField.extractProps(fieldInfo, dynamicInfo),
            readonlyField: dynamicInfo.readonly,
        };
    },
    fieldDependencies: [
        { name: "is_configurable_product", type: "boolean" },
        { name: "product_type", type: "selection" },
        { name: "service_tracking", type: "selection" },
        { name: "product_template_attribute_value_ids", type: "many2many" },
        { name: "translated_product_name", type: "char" },
    ],
};

registry.category("fields").add("sol_product_many2one", saleOrderLineProductField);
