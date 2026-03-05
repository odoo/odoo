import { BaseOptionComponent } from "@html_builder/core/base_option_component";
import { onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";

export class ExtraFieldRowOption extends BaseOptionComponent {
    static id = "extra_field_row_option";
    static template = "website_sale.ExtraFieldRowOption";
    static dependencies = ["extraFieldsOptionPlugin"];

    setup() {
        super.setup();
        const { loadSpecificationsData, getState } = this.dependencies.extraFieldsOptionPlugin;
        this.state = getState();
        this.state.rowCategoryId = null;
        this.currentCategoryId = false;

        const editingElement = this.env.getEditingElement();
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);

        onWillStart(async () => {
            await loadSpecificationsData();
            const currentExtraField = this.state.extraFields.find(
                (extraField) => extraField.id === extraFieldId
            );
            this.currentCategoryId = currentExtraField?.category_id?.[0] || false;
        });
    }

    setCategoryCreateMode(value) {
        this.state.rowCategoryCreateMode = value;
        this.state.newCategoryName = "";
    }

    getAvailableCategories() {
        return this.state.categories.filter((category) => category.id !== this.currentCategoryId);
    }
}

registry.category("website-options").add(ExtraFieldRowOption.id, ExtraFieldRowOption);
