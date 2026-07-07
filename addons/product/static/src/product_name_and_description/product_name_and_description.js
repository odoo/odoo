/** @odoo-module */

import { _t } from "@web/core/l10n/translation";
import { getActiveHotkey } from "@web/core/hotkeys/hotkey_utils";
import { Component, onMounted, onPatched, onWillUnmount, proxy, signal, useProps } from "@odoo/owl";
import { many2OneFieldProps } from "@web/views/fields/many2one/many2one_field";
import { useProductAndLabelAutoresize } from "./product_and_label_autoresize";
import { computeM2OProps, Many2One } from "@web/views/fields/many2one/many2one";
import { useInputField } from "@web/views/fields/input_field_hook";

export const ProductNameAndDescriptionListRendererMixin = {

    getActiveColumns() {
        let activeColumns = super.getActiveColumns();
        const productCol = activeColumns.find((col) => this.productColumns.includes(col.name));
        const labelCol = activeColumns.find((col) => col.name === this.descriptionColumn);

        if (productCol) {
            if (labelCol) {
                this.props.list.records.forEach((record) => (record.columnIsProductAndLabel = true));
            } else {
                this.props.list.records.forEach((record) => (record.columnIsProductAndLabel = false));
            }
            activeColumns = activeColumns.filter((col) => col.name !== this.descriptionColumn);
            this.titleField = productCol.name;
        } else {
            this.titleField = "name";
        }

        return activeColumns;
    }
};

export class ProductNameAndDescriptionField extends Component {
    static components = { Many2One };
    props = useProps({ ...many2OneFieldProps });
    static template = Many2One.template;

    static descriptionColumn = "";

    setup() {
        this.isPrintMode = proxy({ value: false });
        this.labelVisibility = proxy({ value: false });
        this.switchToLabel = false;
        this.labelNode = signal.ref();
        useProductAndLabelAutoresize(this.labelNode, { targetParentName: this.props.name });
        this.productNode = signal.ref();
        useProductAndLabelAutoresize(this.productNode, { targetParentName: this.props.name });

        this.descriptionColumn = this.constructor.descriptionColumn;
        useInputField({
            ref: this.labelNode,
            fieldName: this.descriptionColumn,
            getValue: () => this.label,
        });

        onPatched(() => {
            const labelEl = this.labelNode();
            if (labelEl && this.switchToLabel) {
                this.switchToLabel = false;
                labelEl.focus();
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
        return this.props.record.data[this.props.name].display_name || "";
    }

    get label() {
        return this.props.record.data[this.descriptionColumn];
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

    get columnIsProductAndLabel() {
        return this.props.record.columnIsProductAndLabel;
    }

    get isProductClickable() {
        return this.props.record.evalContext.parent.state !== "draft";
    }

    get showLabelVisibilityToggler() {
        return !this.props.readonly && this.columnIsProductAndLabel && !this.label;
    }

    switchLabelVisibility() {
        this.labelVisibility.value = !this.labelVisibility.value;
        this.switchToLabel = true;
    }

    /**
     * @param {KeyboardEvent} ev
     */
    onM2oInputKeydown(ev) {
        const hotkey = getActiveHotkey(ev);
        if (hotkey === "enter" && this.showLabelVisibilityToggler) {
            this.switchLabelVisibility();
            ev.stopPropagation();
            ev.preventDefault();
        }
    }
}
