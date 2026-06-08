import { _t } from "@web/core/l10n/translation";
import { buildM2OFieldDescription, extractM2OFieldProps, m2oSupportedOptions } from "@web/views/fields/many2one/many2one_field";
import { registry } from "@web/core/registry";
import { ProductNameAndDescriptionField } from "@product/product_name_and_description/product_name_and_description";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { props, t } from "@odoo/owl";

// inlined from Many2OneField.props (via ProductNameAndDescriptionField, both still old-style)
export const productLabelSectionAndNoteFieldProps = {
    ...standardFieldProps,
    canCreate: t.boolean().optional(),
    canCreateEdit: t.boolean().optional(),
    canOpen: t.boolean().optional(),
    canQuickCreate: t.boolean().optional(),
    canScanBarcode: t.boolean().optional(),
    canWrite: t.boolean().optional(),
    context: t.object().optional(),
    decorations: t.object().optional(),
    domain: t.or([t.array(), t.function()]).optional(),
    nameCreateField: t.string().optional(),
    openActionContext: t.string().optional(),
    placeholder: t.string().optional(),
    searchLimit: t.number().optional(),
    searchThreshold: t.number().optional(),
    string: t.string().optional(),
    show_label_warning: t.boolean().optional(false),
};

export class ProductLabelSectionAndNoteField extends ProductNameAndDescriptionField {
    static template = "account.ProductLabelSectionAndNoteField";
    props = props(productLabelSectionAndNoteFieldProps);

    static descriptionColumn = "name";

    get sectionAndNoteClasses() {
        return {
            "fw-bolder": this.isSection,
            "fw-bold": this.isSubSection,
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

    get isSection() {
        return this.props.record.data.display_type === "line_section";
    }

    get isSubSection() {
        return this.props.record.data.display_type === "line_subsection";
    }

    get isSectionOrSubSection() {
        return this.isSection || this.isSubSection;
    }

    isNote(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_note";
    }

    parseLabel(value) {
        return (this.productName && value && this.productName.concat("\n", value))
            || (this.productName && !value && this.productName)
            || (value || "");
    }

    shouldShowWarning() {
        return (
            !this.productName &&
            this.props.show_label_warning &&
            !this.isSectionOrSubSection &&
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
