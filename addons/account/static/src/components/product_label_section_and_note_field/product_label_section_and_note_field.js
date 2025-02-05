import { useProductAndLabelAutoresize } from "@account/core/utils/product_and_label_autoresize";
import {
    Component,
    onMounted,
    onPatched,
    onWillUnmount,
    useEffect,
    useRef,
    useState,
} from "@odoo/owl";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Many2One, useMany2One } from "@web/views/fields/many2one/many2one";
import { Many2OneField, many2OneField } from "@web/views/fields/many2one/many2one_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";

export class ProductLabelSectionAndNoteAutocomplete extends AutoComplete {
    setup() {
        super.setup();
        this.labelTextarea = useRef("labelNodeRef");
    }
    onInputKeydown(event) {
        super.onInputKeydown(event);
        const hotkey = getActiveHotkey(event);
        const labelVisibilityButton = document.getElementById('labelVisibilityButtonId');
        if (hotkey === "enter") {
            if (labelVisibilityButton && !this.labelTextarea.el) {
                labelVisibilityButton.click();
                event.stopPropagation();
                event.preventDefault();
            }
        }
    }
}

export class ProductLabelSectionAndNoteFieldAutocomplete extends Many2XAutocomplete {
    static components = {
        ...Many2XAutocomplete.components,
        AutoComplete: ProductLabelSectionAndNoteAutocomplete,
    };
    static props = {
        ...Many2XAutocomplete.props,
        isNote: { type: Boolean },
        isSection: { type: Boolean },
        onFocusout: { type: Function, optional: true },
        updateLabel: { type: Function, optional: true },
    };
    static template = "account.ProductLabelSectionAndNoteFieldAutocomplete";
    setup() {
        super.setup();
        this.input = useRef("section_and_note_input");
    }

    get isSectionOrNote() {
        return this.props.isSection || this.props.isNote;
    }

    get isSection() {
        return this.props.isSection;
    }
}

export class ProductLabelSectionAndNoteField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: ProductLabelSectionAndNoteFieldAutocomplete,
    };
    static template = "account.ProductLabelSectionAndNoteField";

    setup() {
        super.setup();
        this.isPrintMode = useState({ value: false });
        this.labelVisibility = useState({ value: false });
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
    }

    get productName() {
        return this.props.record.data[this.props.name][1];
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

    get Many2XAutocompleteProps() {
        const props = super.Many2XAutocompleteProps;
        props.isSection = this.isSection(this.props.record);
        props.isNote = this.isNote(this.props.record);
        props.placeholder = _t("Search a product");
        props.updateLabel = this.updateLabel.bind(this);
        return props;
    }

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
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

    switchLabelVisibility() {
        this.labelVisibility.value = !this.labelVisibility.value;
        this.switchToLabel = true;
    }

    updateLabel(value) {
        this.props.record.update({
          name:
            this.productName && this.productName !== value
              ? `${this.productName}\n${value}`
              : value,
        });
    }
}

export const productLabelSectionAndNoteField = {
    ...many2OneField,
    listViewWidth: [240, 400],
    component: ProductLabelSectionAndNoteField,
};
// registry
//     .category("fields")
//     .add("product_label_section_and_note_field", productLabelSectionAndNoteField);

class MyPLSN extends Component {
    static template = "account.MyPLSN";
    static components = { Many2One };

    setup() {
        this.m2o = useMany2One(() => this.props);

        this.labelNode = useRef("labelNodeRef");
        this.productNode = useRef("productNodeRef");

        this.switchToLabel = false;
        this.isPrintMode = useState({ value: false });
        this.labelVisibility = useState({ value: false });
        this.columnIsProductAndLabel = useState({
            value: this.props.record.columnIsProductAndLabel,
        });

        useProductAndLabelAutoresize(this.labelNode, { targetParentName: this.props.name });
        useProductAndLabelAutoresize(this.productNode, { targetParentName: this.props.name });

        useEffect(
            (columnIsProductAndLabel) => {
                this.columnIsProductAndLabel.value = columnIsProductAndLabel;
            },
            () => [this.props.record.columnIsProductAndLabel]
        );

        onPatched(() => {
            if (this.labelNode.el && this.switchToLabel) {
                this.switchToLabel = false;
                this.labelNode.el.focus();
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
        return this.props.record.data.name;
    }

    get m2oProps() {
        return {
            ...this.m2o.computeProps(),
            // isNote: this.isNote,
            // isSection: this.isSection,
            placeholder: _t("Search a product"),
            // updateLabel: (value) => this.updateLabel(value),
        };
    }

    updateLabel(value) {
        return this.props.record.update({
            name: value,
        });
    }
}

registry.category("fields").add("product_label_section_and_note_field", {
    component: MyPLSN,
    fieldDependencies: [
        { name: "name", type: "char" },
        { name: "display_type", type: "selection" },
    ],
});
