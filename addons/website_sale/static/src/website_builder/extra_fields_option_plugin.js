import { proxy } from "@odoo/owl";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

class ExtraFieldsPlugin extends Plugin {
    static id = "extraFieldsOption";
    static shared = [
        "clearLoadedExtraFields",
        "getExtraFields",
        "getCategories",
        "loadExtraFields",
        "getState",
        "createAndSelectCategory",
    ];

    _extraFields = proxy([]);
    _categories = proxy([]);
    _state = proxy({
        fieldId: false,
        categoryId: false,
        newCategoryName: "",
        rowCategoryId: null,
        categoryCreateMode: false,
        rowCategoryCreateMode: false,
    });
    _loadedExtraFields = null;

    resources = {
        builder_actions: {
            AddExtraFieldAction,
            CreateCategoryAction,
            CreateRowCategoryAction,
            DeleteExtraFieldAction,
            ChangeExtraFieldCategoryAction,
            SelectExtraFieldAction,
            SelectExtraFieldCategoryAction,
            SetExtraFieldCategoryNameAction,
            SelectExtraFieldRowCategoryAction,
        },
    };

    getExtraFields() {
        return this._extraFields;
    }

    getCategories() {
        return this._categories;
    }

    getState() {
        return this._state;
    }

    async loadExtraFields() {
        if (!this._loadedExtraFields) {
            const websiteId = this.services.website.currentWebsite.id;

            const [modelFields, categories, extraFields] = await Promise.all([
                this.services.orm.searchRead(
                    "ir.model.fields",
                    [
                        ["model", "=", "product.template"],
                        ["ttype", "in", ["binary", "char", "float"]],
                    ],
                    ["id", "name", "field_description", "model"]
                ),
                this.services.orm.searchRead(
                    "product.attribute.category",
                    [],
                    ["id", "name"]
                ),
                this.services.orm.searchRead(
                    "website.sale.extra.field",
                    [["website_id", "=", websiteId]],
                    ["id", "field_id", "category_id", "label", "name"]
                ),
            ]);

            this._categories.splice(0, this._categories.length, ...categories);
            this._extraFields.splice(0, this._extraFields.length, ...extraFields);
            this._loadedExtraFields = { fields: modelFields };
        }
        return this._loadedExtraFields;
    }

    clearLoadedExtraFields() {
        this._loadedExtraFields = null;
    }

    async createAndSelectCategory({ selectedCategoryKey, createModeKey }) {
        const state = this.getState();
        const categoryName = state.newCategoryName.trim();
        if (!categoryName) {
            return;
        }

        const [newCategoryId] = await this.services.orm.create(
            "product.attribute.category",
            [{ name: categoryName }]
        );

        this.getCategories().push({ id: newCategoryId, name: categoryName });

        state[selectedCategoryKey] = newCategoryId;
        state.newCategoryName = "";
        state[createModeKey] = false;
        this.clearLoadedExtraFields();
    }
}

class AddExtraFieldAction extends BuilderAction {
    static id = "addExtraField";
    static dependencies = ["extraFieldsOption"];

    setup() {
        this.reload = {};
    }

    async apply() {
        const state = this.dependencies.extraFieldsOption.getState();
        const fieldId = state.fieldId;
        const categoryId = state.categoryId || false;

        if (!fieldId) {
            return;
        }

        const extraFields = this.dependencies.extraFieldsOption.getExtraFields();
        if (extraFields.some((extraField) => extraField.field_id[0] === fieldId)) {
            return;
        }

        const websiteId = this.services.website.currentWebsite.id;
        await this.services.orm.create(
            "website.sale.extra.field",
            [{ website_id: websiteId, field_id: fieldId, category_id: categoryId }]
        );

        state.fieldId = false;
        state.categoryId = false;
        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }
}

class CreateCategoryAction extends BuilderAction {
    static id = "createCategory";
    static dependencies = ["extraFieldsOption"];

    async apply() {
        await this.dependencies.extraFieldsOption.createAndSelectCategory({
            selectedCategoryKey: "categoryId",
            createModeKey: "categoryCreateMode",
        });
    }
}

class CreateRowCategoryAction extends BuilderAction {
    static id = "createRowCategory";
    static dependencies = ["extraFieldsOption"];

    async apply() {
        await this.dependencies.extraFieldsOption.createAndSelectCategory({
            selectedCategoryKey: "rowCategoryId",
            createModeKey: "rowCategoryCreateMode",
        });
    }
}

class DeleteExtraFieldAction extends BuilderAction {
    static id = "deleteExtraField";
    static dependencies = ["extraFieldsOption"];

    setup() {
        this.reload = {};
    }

    async apply({ editingElement }) {
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        if (!extraFieldId) {
            return;
        }

        await this.services.orm.unlink("website.sale.extra.field", [extraFieldId]);
        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }
}

class ChangeExtraFieldCategoryAction extends BuilderAction {
    static id = "changeExtraFieldCategory";
    static dependencies = ["extraFieldsOption"];

    setup() {
        this.reload = {};
    }

    async apply({ editingElement }) {
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        if (!extraFieldId) return;

        const state = this.dependencies.extraFieldsOption.getState();
        if (state.rowCategoryId === null) return;

        await this.services.orm.write(
            "website.sale.extra.field",
            [extraFieldId],
            { category_id: state.rowCategoryId || false }
        );

        state.rowCategoryId = null;
        this.dependencies.extraFieldsOption.clearLoadedExtraFields();
    }

}

class SelectExtraFieldAction extends BuilderAction {
    static id = "selectExtraField";
    static dependencies = ["extraFieldsOption"];

    isApplied({ value }) {
        const fieldId = this.dependencies.extraFieldsOption.getState().fieldId;
        return String(fieldId || "") === String(value || "");
    }

    getValue() {
        return String(this.dependencies.extraFieldsOption.getState().fieldId || "");
    }

    apply({ value }) {
        this.dependencies.extraFieldsOption.getState().fieldId = parseInt(value) || false;
    }
}

class SelectExtraFieldCategoryAction extends BuilderAction {
    static id = "selectExtraFieldCategory";
    static dependencies = ["extraFieldsOption"];

    isApplied({ value }) {
        const categoryId = this.dependencies.extraFieldsOption.getState().categoryId;
        return String(categoryId || "") === String(value || "");
    }

    getValue() {
        return String(this.dependencies.extraFieldsOption.getState().categoryId || "");
    }

    apply({ value }) {
        this.dependencies.extraFieldsOption.getState().categoryId = parseInt(value) || false;
    }
}

class SetExtraFieldCategoryNameAction extends BuilderAction {
    static id = "setExtraFieldCategoryName";
    static dependencies = ["extraFieldsOption"];

    getValue() {
        return this.dependencies.extraFieldsOption.getState().newCategoryName;
    }

    apply({ value }) {
        this.dependencies.extraFieldsOption.getState().newCategoryName = value || "";
    }
}

class SelectExtraFieldRowCategoryAction extends BuilderAction {
    static id = "selectExtraFieldRowCategory";
    static dependencies = ["extraFieldsOption"];

    isApplied({ value }) {
        const rowCategoryId = this.dependencies.extraFieldsOption.getState().rowCategoryId;
        return rowCategoryId !== null && String(rowCategoryId || "") === String(value || "");
    }

    getValue() {
        const rowCategoryId = this.dependencies.extraFieldsOption.getState().rowCategoryId;
        return rowCategoryId === null ? "" : String(rowCategoryId || "");
    }

    apply({ value }) {
        this.dependencies.extraFieldsOption.getState().rowCategoryId =
            value === "" ? false : parseInt(value);
    }
}

registry.category("website-plugins").add(ExtraFieldsPlugin.id, ExtraFieldsPlugin);
