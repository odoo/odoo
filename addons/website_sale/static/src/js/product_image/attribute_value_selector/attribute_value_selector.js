import { Component, onWillStart, proxy } from "@odoo/owl";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { useDropdownState } from "@web/core/dropdown/dropdown_hooks";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { _t } from "@web/core/l10n/translation";
import { x2ManyCommands } from "@web/core/orm_service";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class AttributeValueSelector extends Component {
    static template = "website_sale.attribute_value_selector";
    static components = { Dropdown, DropdownItem };
    static props = {
        ...standardFieldProps,
    };

    setup() {
        this.orm = useService("orm");
        this.state = proxy({
            selectedValues: new Set(),
        });

        this.dropdownState = useDropdownState();

        onWillStart(async () => {
            if (!this.showDropdown) {
                return;
            }

            this.attributeValueMapping = await this.orm.call(
                "product.template",
                "get_attribute_value_mapping",
                [this.props.record.data.product_tmpl_id.id]
            );
        });
    }

    get badgeLabel() {
        const record = this.props.record;
        return (
            (record._parentRecord?.resModel === "product.template" &&
                record.fields.image_type.selection.find(
                    ([key]) => key === record.data.image_type
                )?.[1]) ||
            ""
        );
    }

    get showDropdown() {
        return this.props.record._parentRecord.data.product_variant_count > 1;
    }

    get selectedValuesCount() {
        return this.props.record.data[this.props.name].count || _t("All");
    }

    /**
     * Synchronize the local selection state with the current field values before
     * the dropdown is opened.
     */
    async beforeOpen() {
        this.state.selectedValues = new Set(this.props.record.data[this.props.name].currentIds);
    }

    /**
     * Add or remove an attribute value from the current selection.
     *
     * @param {number} valueId - The ID of the attribute value to toggle.
     */
    async toggleValue(valueId) {
        const selectedValues = this.state.selectedValues;
        const isSelected = selectedValues.has(valueId);

        isSelected ? selectedValues.delete(valueId) : selectedValues.add(valueId);
    }

    /**
     * When the dropdown closes, update the record only if the selected values have changed.
     * Updates are applied on close to avoid triggering a record update for each selection change.
     *
     * @param {boolean} isOpen - Indicates whether the dropdown is currently open.
     */
    onDropdownStateChanged(isOpen) {
        if (!isOpen) {
            const initialValues = this.props.record.data[this.props.name].currentIds || [];
            const finalValues = [...this.state.selectedValues];

            if (
                initialValues.length === finalValues.length &&
                initialValues.every((value) => finalValues.includes(value))
            ) {
                return;
            }

            this.props.record.update({
                [this.props.name]: [x2ManyCommands.set(finalValues)],
            });
        }
    }
}

const attributeValueSelector = { component: AttributeValueSelector };

registry.category("fields").add("attribute_value_selector", attributeValueSelector);
