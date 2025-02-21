import { registry } from "@web/core/registry";
import { many2OneField } from "@web/views/fields/many2one/many2one_field";
import { ProductLabelSectionAndNoteFieldAutocomplete, ProductLabelSectionAndNoteAutocomplete, ProductLabelSectionAndNoteField } from "@account/components/product_label_section_and_note_field/product_label_section_and_note_field";

export class PurchaseProductLabelSectionAutocomplete extends ProductLabelSectionAndNoteAutocomplete {
    static template = "purchase.PurchaseProductLabelSectionAutocomplete";
    static props = {
        ...ProductLabelSectionAndNoteAutocomplete.props,
        resModel: { type: String, optional: true },
    };

    setup() {
        super.setup();
        this.count = [];
        this.ormcall().then((count) => {
            this.count = count;
        })
    }

    async ormcall() {
        if (this.env.model.root.data.partner_id) {
            let context = {partner_id: this.env.model.root.data.partner_id[0]}
            if (this.props.resModel == 'product.product') {
                context['is_product_id'] = true
            }
            return await this.env.model.orm.call('product.template', 'get_prioritized_product', [{}, 'purchase'], {context : context});
        }
        return []
    }

    isPrioritized() {
        return this.count.includes(this.option.value);
    }
}

export class PurchaseProductLabelSectionFieldAutocomplete extends ProductLabelSectionAndNoteFieldAutocomplete {
    static template = "purchase.PurchaseProductLabelSectionFieldAutocomplete";
    static components = {
        ...ProductLabelSectionAndNoteFieldAutocomplete.components,
        AutoComplete: PurchaseProductLabelSectionAutocomplete,
    };
    static props = {
        ...ProductLabelSectionAndNoteFieldAutocomplete.props,
        resModel: { type: String, optional: true },
    }
}

export class PurchaseProductLabelSectionField extends ProductLabelSectionAndNoteField {
    static components = {
        ...ProductLabelSectionAndNoteField.components,
        Many2XAutocomplete: PurchaseProductLabelSectionFieldAutocomplete,
    };
}

export const purchaseProductLabelSectionField = {
    ...many2OneField,
    component: PurchaseProductLabelSectionField,
};
registry.category("fields").add("product_label_section_purchase", purchaseProductLabelSectionField);
