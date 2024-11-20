/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_service";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { onMounted, onPatched, onWillUnmount, useEffect, useRef, useState } from "@odoo/owl";
import { Many2OneField } from "@web/views/fields/many2one/many2one_field";
import { useProductAndLabelAutoresize } from "./product_and_label_autoresize";

export const ProductNameAndDescriptionListRendererMixin = {
    getCellTitle(column, record) {
        // When using this list renderer, we don't want the product_id cell to have a tooltip with its label.
        if (this.productColumns.includes(column.name)) {
            return;
        }
        super.getCellTitle(column, record);
    },
    getActiveColumns(list) {
        let activeColumns = super.getActiveColumns(list);
        const productCol = activeColumns.find((col) => this.productColumns.includes(col.name));
        const labelCol = activeColumns.find((col) => col.name === this.descriptionColumn);
        if (productCol) {
            if (labelCol) {
                list.records.forEach((record) => (record.columnIsProductAndLabel = true));
            } else {
                list.records.forEach((record) => (record.columnIsProductAndLabel = false));
            }
            activeColumns = activeColumns.filter((col) => col.name !== this.descriptionColumn);
            this.titleField = productCol.name;
        } else {
            this.titleField = this.descriptionColumn;
        }

        return activeColumns;
    }
};

export class ProductLabelAutocomplete extends AutoComplete {
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

export class ProductLabelFieldAutocomplete extends Many2XAutocomplete {
    static components = {
        ...super.components,
        AutoComplete: ProductLabelAutocomplete,
    };
    static props = {
        ...super.props,
        onFocusout: { type: Function, optional: true },
        updateLabel: { type: Function, optional: true },
    };
    static template = "product.ProductLabelFieldAutocomplete";

    setup() {
        super.setup();
        this.input = useRef("section_and_note_input");
    }
}

export class ProductNameAndDescriptionField extends Many2OneField {
    static components = {
        ...Many2OneField.components,
        Many2XAutocomplete: ProductLabelFieldAutocomplete,
    };

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
        let label = this.props.record.data[this.descriptionColumn];
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
        props.placeholder = _t("Search a product");
        props.updateLabel = this.updateLabel.bind(this);
        return props;
    }

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get recordState() {
        return this.props.record.model.root.data.state;
    }

    switchLabelVisibility() {
        this.labelVisibility.value = !this.labelVisibility.value;
        this.switchToLabel = true;
    }

    updateLabel(value) {
        this.props.record.update({
          [this.descriptionColumn]:
            this.productName && this.productName !== value
              ? `${this.productName}\n${value}`
              : value,
        });
    }
}
