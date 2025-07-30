import { _t } from "@web/core/l10n/translation";
import { buildM2OFieldDescription, extractM2OFieldProps, m2oSupportedOptions } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import { ProductNameAndDescriptionField } from "@product/product_name_and_description/product_name_and_description";

export class ProductLabelSectionAndNoteField extends ProductNameAndDescriptionField {
    static template = "account.ProductLabelSectionAndNoteField";
    static props = {
        ...super.props,
        show_label_warning: { type: Boolean, optional: true, default: false },
    };

    static descriptionColumn = "name";

    get sectionAndNoteClasses() {
        return {
            "fw-bolder": this.isTopSection(),
            "fw-bold": this.isSection() && !this.isTopSection(),
            "fst-italic": this.isNote(),
            "text-warning": this.shouldShowWarning(),
        };
    }

    get sectionAndNoteIsReadonly() {
        return (
            this.props.readonly
            && this.isProductClickable
            && (["cancel", "posted"].includes(this.props.record.evalContext.parent.state)
            || this.props.record.evalContext.parent.locked)
        )
    }

    isSection(record = null) {
        record = record || this.props.record;
        return ["line_section", "line_subsection"].includes(record.data.display_type);
    }

    isTopSection(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_section";
    }

    isNote(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_note";
    }

    shouldShowWarning() {
        return (
            !this.productName &&
            this.props.show_label_warning &&
            !this.isSection() &&
            !this.isNote()
        );
    }
}

export const productLabelSectionAndNoteField = {
    ...buildM2OFieldDescription(ProductLabelSectionAndNoteField),
    listViewWidth: [240, 400],
    supportedOptions: [
        ...m2oSupportedOptions,
        {
            label: _t("Show Label Warning"),
            name: "show_label_warning",
            type: "boolean",
            default: false
        },
    ],
    extractProps({ options }) {
        const props = extractM2OFieldProps(...arguments);
        props.show_label_warning = options.show_label_warning;
        return props;
    },
};
registry
    .category("fields")
    .add("product_label_section_and_note_field", productLabelSectionAndNoteField);
