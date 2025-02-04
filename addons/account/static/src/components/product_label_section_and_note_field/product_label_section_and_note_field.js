import { many2OneField } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import {
    SectionAndNoteListRenderer,
    sectionAndNoteFieldOne2Many,
} from "@account/components/section_and_note_fields_backend/section_and_note_fields_backend";
import { X2ManyField, x2ManyField } from "@web/views/fields/x2many/x2many_field";
import { 
    ProductNameAndDescriptionListRendererMixin,
    ProductLabelFieldAutocomplete,
    ProductNameAndDescriptionField
} from "@product/product_name_and_description/product_name_and_description";
import { patch } from "@web/core/utils/patch";

export class ProductLabelSectionAndNoteListRender extends SectionAndNoteListRenderer {
    setup() {
        super.setup();
        this.descriptionColumn = "name";
        this.productColumns = ["product_id", "product_template_id"];
    }
}

patch(ProductLabelSectionAndNoteListRender.prototype, ProductNameAndDescriptionListRendererMixin);

export class ProductLabelSectionAndNoteOne2Many extends X2ManyField {
    static components = {
        ...X2ManyField.components,
        ListRenderer: ProductLabelSectionAndNoteListRender,
    };
}

export const productLabelSectionAndNoteOne2Many = {
    ...x2ManyField,
    component: ProductLabelSectionAndNoteOne2Many,
    additionalClasses: sectionAndNoteFieldOne2Many.additionalClasses,
};

registry
    .category("fields")
    .add("product_label_section_and_note_field_o2m", productLabelSectionAndNoteOne2Many);

export class ProductLabelSectionAndNoteFieldAutocomplete extends ProductLabelFieldAutocomplete {
    static props = {
        ...super.props,
        isNote: { type: Boolean },
        isSection: { type: Boolean },
    };
    static template = "account.ProductLabelSectionAndNoteFieldAutocomplete";

    get isSectionOrNote() {
        return this.props.isSection || this.props.isNote;
    }

    get isSection() {
        return this.props.isSection;
    }
}

export class ProductLabelSectionAndNoteField extends ProductNameAndDescriptionField {
    static template = "account.ProductLabelSectionAndNoteField";
    static components = {
        ...super.components,
        Many2XAutocomplete: ProductLabelSectionAndNoteFieldAutocomplete,
    };

    setup() {
        super.setup();
        this.descriptionColumn = "name";
    }

    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        props.isSection = this.isSection(this.props.record);
        props.isNote = this.isNote(this.props.record);
        return props;
    }

    get isSectionOrNote() {
        return this.isSection(this.props.record) || this.isNote(this.props.record);
    }

    get sectionAndNoteClasses() {
        if (this.isSection()) {
            return "fw-bold";
        } else if (this.isNote()) {
            return "fst-italic";
        }
        return "";
    }

    isSection(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_section";
    }

    isNote(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_note";
    }
}

export const productLabelSectionAndNoteField = {
    ...many2OneField,
    listViewWidth: [240, 400],
    component: ProductLabelSectionAndNoteField,
};
registry
    .category("fields")
    .add("product_label_section_and_note_field", productLabelSectionAndNoteField);
