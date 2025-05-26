import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Component, onMounted, onPatched, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useProductAndLabelAutoresize } from "@account/core/utils/product_and_label_autoresize";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { useService } from "@web/core/utils/hooks";
import { formatDuration } from "@web/core/l10n/dates";

class ProductLabelSectionAndNoteFieldAutocomplete extends AutoComplete {
    onInputKeydown(event) {
        super.onInputKeydown(event);
        const hotkey = getActiveHotkey(event);
        const labelVisibilityButton = document.getElementById('labelVisibilityButtonId');
        if (hotkey === "enter" && labelVisibilityButton) {
            labelVisibilityButton.click();
            event.stopPropagation();
            event.preventDefault();
        }
    }
}

class ProductLabelSectionAndNoteFieldMany2XAutocomplete extends Many2XAutocomplete {
    static components = {
        ...super.components,
        AutoComplete: ProductLabelSectionAndNoteFieldAutocomplete,
    };
}
class ProductLabelSectionAndNoteFieldMany2One extends Many2One {
    static components = {
        ...super.components,
        Many2XAutocomplete: ProductLabelSectionAndNoteFieldMany2XAutocomplete,
    };
}

export class ProductLabelSectionAndNoteField extends Component {
    static template = "account.ProductLabelSectionAndNoteField";
    static components = { Many2One: ProductLabelSectionAndNoteFieldMany2One };
    static props = { ...Many2OneField.props };

    setup() {
        super.setup();
        this.isPrintMode = useState({ value: false });
        this.labelVisibility = useState({ value: false });
        this.orm = useService("orm");
        this.switchToLabel = false;
        this.columnIsProductAndLabel = useState({ value: this.props.record.columnIsProductAndLabel });
        this.labelNode = useRef("labelNodeRef");
        useProductAndLabelAutoresize(this.labelNode, { targetParentName: this.props.name });
        this.productNode = useRef("productNodeRef");
        useProductAndLabelAutoresize(this.productNode, { targetParentName: this.props.name });

        useEffect(
            () => {
                this.columnIsProductAndLabel.value = this.props.record.columnIsProductAndLabel;
            },
            () => [this.props.record.columnIsProductAndLabel]
        );

        onPatched(() => {
            if (this.labelNode.el && this.switchToLabel) {
                this.switchToLabel = false;
                this.labelNode.el.focus();
            }
        });

        this.onBeforePrint = () => {
            this.isPrintMode.value = true;
        };

        this.onAfterPrint = () => {
            this.isPrintMode.value = false;
        };

        // The following hooks are used to make a div visible only in the print view. This div is necessary in the
        // print view in order not to have scroll bars but can't be displayed in the normal view because it adds
        // an empty line. This is done by switching an attribute to true only during the print view life cycle and
        // including the said div in a t-if depending on that attribute.
        onMounted(() => {
            window.addEventListener("beforeprint", this.onBeforePrint);
            window.addEventListener("afterprint", this.onAfterPrint);
        });

        onWillUnmount(() => {
            window.removeEventListener("beforeprint", this.onBeforePrint);
            window.removeEventListener("afterprint", this.onAfterPrint);
        });

        this.get_prioritized_product().then((prioritized_product) => {
            this.prioritized_product = prioritized_product;
        })
    }

    async get_prioritized_product() {
        if (this.props.context.partner_id && this.props.context.move_type == 'out_invoice') {
            return await this.orm.call(
                'product.template',
                'get_prioritized_product_and_time',
                [{}, 'sale'],
                {context: {partner_id: this.props.context.partner_id}});
        }
        return []
    }

    computeTime() {
        if (this.prioritized_product) {
            const product_data = this.prioritized_product.filter(key => key.product_id == this.autoCompleteItemScope.value)
            if (product_data.length > 0) {
                const duration = (new Date() - new Date(product_data[0].invoice_date)) / 1000
                if ((duration / (24 * 3600)) > 1) {
                    return formatDuration(duration, false);
                }
                return '0d'
            }
            return ''
        }
        return ''
    }

    get productName() {
        return this.props.record.data[this.props.name].display_name;
    }

    get label() {
        let label = this.props.record.data.name;
        if (label.includes(this.productName)) {
            label = label.replace(this.productName, "");
            if (label.includes("\n")) {
                label = label.replace("\n", "");
            }
        }
        return label;
    }

    get m2oProps() {
        const p = computeM2OProps(this.props);
        let value = p.value && { ...p.value };
        if (this.props.readonly && this.productName) {
            value = { ...value, display_name: this.productName };
        }
        return {
            ...p,
            canOpen: !this.props.readonly || this.isProductClickable,
            placeholder: _t("Search a product"),
            value,
        };
    }

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get sectionAndNoteClasses() {
        return {
            "fw-bold": this.isSection(),
            "fst-italic": this.isNote(),
        };
    }

    get sectionAndNoteIsReadonly() {
        return (
            this.props.readonly
            && this.isProductClickable
            && (["cancel", "posted"].includes(this.props.record.evalContext.parent.state)
            || this.props.record.evalContext.parent.locked)
        )
    };

    isSection(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_section";
    }

    isNote(record = null) {
        record = record || this.props.record;
        return record.data.display_type === "line_note";
    }

    switchLabelVisibility() {
        this.labelVisibility.value = !this.labelVisibility.value;
        this.switchToLabel = true;
    }

    updateLabel(value) {
        this.props.record.update({
            name: (
                this.productName && value && this.productName.concat("\n", value)
                || !value && this.productName
                || value
            ),
        });
    }
}

export const productLabelSectionAndNoteField = {
    ...buildM2OFieldDescription(ProductLabelSectionAndNoteField),
    listViewWidth: [240, 400],
};
registry
    .category("fields")
    .add("product_label_section_and_note_field", productLabelSectionAndNoteField);
