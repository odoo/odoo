import { _t } from "@web/core/l10n/translation";
import {
    buildM2OFieldDescription,
    many2OneFieldProps,
} from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import { Component, useProps } from "@odoo/owl";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";

export class ProductLabelSectionAndNoteField extends Component {
    static template = "account.ProductLabelSectionAndNoteField";
    static components = { Many2One };
    props = useProps(many2OneFieldProps);

    get productName() {
        return this.props.record.data[this.props.name].display_name || "";
    }

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get m2oProps() {
        const p = computeM2OProps(this.props);
        let value = p.value && { ...p.value };
        if (this.props.readonly && this.productName) {
            value = { ...value, display_name: this.productName };
        }
        return {
            ...p,
            canOpen: p.canOpen && (!this.props.readonly || this.isProductClickable),
            placeholder: _t("Search a product"),
            preventMemoization: true,
            value,
        };
    }
}

export const productLabelSectionAndNoteField = {
    ...buildM2OFieldDescription(ProductLabelSectionAndNoteField),
    listViewWidth: [240, 400],
};

registry
    .category("fields")
    .add("product_label_section_and_note_field", productLabelSectionAndNoteField);
