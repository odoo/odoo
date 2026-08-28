import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart, proxy } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ExtraFieldsOption extends BaseOptionComponent {
    static id = "extra_fields_option";
    static template = "website_sale.ExtraFieldsOption";
    static dependencies = ["extraFieldsOption"];

    setup() {
        super.setup();
        const { loadExtraFields, getExtraFields, getCategories, getState } =
            this.dependencies.extraFieldsOption;

        this.sharedState = proxy({
            extraFields: getExtraFields(),
            categories: getCategories(),
            optionState: getState(),
        });

        this.state = proxy({
            fields: [],
        });

        onWillStart(async () => {
            const extraFieldsData = await loadExtraFields();
            this.state.fields = extraFieldsData.fields;

            const displayNameField = this.getAvailableFields().find(
                (field) => field.name === "display_name"
            );
            if (displayNameField && !this.sharedState.optionState.fieldId) {
                this.sharedState.optionState.fieldId = displayNameField.id;
            }
        });
    }

    setCategoryCreateMode(value) {
        this.sharedState.optionState.categoryCreateMode = value;
        this.sharedState.optionState.newCategoryName = "";
    }

    getAvailableFields() {
        const selectedFieldIds = new Set(
            this.sharedState.extraFields.map((extraField) => extraField.field_id[0])
        );
        return this.state.fields.filter((field) => !selectedFieldIds.has(field.id));
    }
}

registry.category("website-options").add(ExtraFieldsOption.id, ExtraFieldsOption);
