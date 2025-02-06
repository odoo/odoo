import { useProductAndLabelAutoresize } from "@account/core/utils/product_and_label_autoresize";
import { Component, onMounted, onPatched, onWillUnmount, useRef, useState } from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { buildM2OFieldDescription, Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

class ProductLabelSectionAndNoteFieldAutocomplete extends AutoComplete {
    async onInputKeydown(event) {
        super.onInputKeydown(event);
        const hotkey = getActiveHotkey(event);
        const labelVisibilityButton = document.getElementById("labelVisibilityButtonId");
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
        AutoComplete: ProductLabelSectionAndNoteFieldMany2XAutocomplete,
    };
}

export class ProductLabelSectionAndNoteField extends Component {
    static template = "account.ProductLabelSectionAndNoteField";
    static components = { Many2One: ProductLabelSectionAndNoteFieldMany2One };
    static props = { ...Many2OneField.props };

    setup() {
        const labelNode = useRef("labelNodeRef");
        const productNode = useRef("productNodeRef");

        this.switchToLabel = false;
        this.isPrintMode = useState({ value: false });
        this.labelVisibility = useState({ value: false });

        useProductAndLabelAutoresize(labelNode, { targetParentName: this.props.name });
        useProductAndLabelAutoresize(productNode, { targetParentName: this.props.name });

        onPatched(() => {
            if (labelNode.el && this.switchToLabel) {
                this.switchToLabel = false;
                labelNode.el.focus();
            }
        });

        const onBeforePrint = () => {
            this.isPrintMode.value = true;
        };
        const onAfterPrint = () => {
            this.isPrintMode.value = false;
        };

        // The following hooks are used to make a div visible only in the print view. This div is necessary in the
        // print view in order not to have scroll bars but can't be displayed in the normal view because it adds
        // an empty line. This is done by switching an attribute to true only during the print view life cycle and
        // including the said div in a t-if depending on that attribute.
        onMounted(() => {
            window.addEventListener("beforeprint", onBeforePrint);
            window.addEventListener("afterprint", onAfterPrint);
        });
        onWillUnmount(() => {
            window.removeEventListener("beforeprint", onBeforePrint);
            window.removeEventListener("afterprint", onAfterPrint);
        });
    }

    get columnIsProductAndLabel() {
        return this.props.record.columnIsProductAndLabel;
    }

    get isNote() {
        return this.props.record.data.display_type === "line_note";
    }

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get isSection() {
        return this.props.record.data.display_type === "line_section";
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
        return {
            ...computeM2OProps(this.props),
            canOpen: !this.props.readonly || this.isProductClickable,
            placeholder: _t("Search a product"),
        };
    }

    get productName() {
        const value = this.props.record.data[this.props.name];
        return value && value[1];
    }

    switchLabelVisibility() {
        this.labelVisibility.value = !this.labelVisibility.value;
        this.switchToLabel = true;
    }

    updateLabel(value) {
        return this.props.record.update({
            name:
                this.productName && this.productName !== value
                    ? `${this.productName}\n${value}`
                    : value,
        });
    }
}

export const productLabelSectionAndNoteField = {
    ...buildM2OFieldDescription(ProductLabelSectionAndNoteField),
    listViewWidth: [240, 400],
    fieldDependencies: [
        { name: "name", type: "char" },
        { name: "display_type", type: "selection" },
    ],
};

registry
    .category("fields")
    .add("product_label_section_and_note_field", productLabelSectionAndNoteField);
