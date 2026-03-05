import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ExtraFieldsOption extends BaseOptionComponent {
    static id = "extra_fields_option";
    static template = "website_sale.ExtraFieldsOption";
    static dependencies = ["extraFieldsOptionPlugin"];

    setup() {
        super.setup();
        const { loadSpecificationsData, getState } = this.dependencies.extraFieldsOptionPlugin;
        this.state = getState();

        onWillStart(async () => {
            await loadSpecificationsData();

            const displayNameField = this.getAvailableFields().find(
                (field) => field.name === "display_name"
            );
            if (displayNameField && !this.state.fieldId) {
                this.state.fieldId = displayNameField.id;
            }
        });
    }

    setCategoryCreateMode(value) {
        this.state.categoryCreateMode = value;
        this.state.newCategoryName = "";
    }

    getAvailableFields() {
        const selectedFieldIds = new Set(
            this.state.extraFields.map((extraField) => extraField.field_id[0])
        );
        return this.state.fields.filter((field) => !selectedFieldIds.has(field.id));
    }
}

registry.category("website-options").add(ExtraFieldsOption.id, ExtraFieldsOption);
