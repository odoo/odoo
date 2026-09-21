import { proxy } from "@odoo/owl";
import { BuilderAction } from "@html_builder/core/builder_action";
import { Plugin } from "@html_editor/plugin";
import { registry } from "@web/core/registry";

export class ExtraFieldsOptionPlugin extends Plugin {
    static id = "extraFieldsOptionPlugin";
    static shared = ["loadSpecificationsData", "getState", "createAndSelectCategory"];

    _state = proxy({
        fields: [],
        categories: [],
        extraFields: [],
        fieldId: false,
        categoryId: false,
        newCategoryName: "",
        rowCategoryId: null,
        categoryCreateMode: false,
        rowCategoryCreateMode: false,
    });
    _specificationsProm = null;

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

    getState() {
        return this._state;
    }

    loadSpecificationsData() {
        if (!this._specificationsProm) {
            const websiteId = this.services.website.currentWebsite.id;
            this._specificationsProm = Promise.all([
                this.services.orm.searchRead(
                    "ir.model.fields",
                    [
                        ["model", "=", "product.template"],
                        ["ttype", "in", ["binary", "char", "float"]],
                    ],
                    ["id", "name", "field_description"]
                ),
                this.services.orm.searchRead("product.attribute.category", [], ["id", "name"]),
                this.services.orm.searchRead(
                    "website.sale.extra.field",
                    [["website_id", "=", websiteId]],
                    ["id", "field_id", "category_id"]
                ),
            ]).then(([fields, categories, extraFields]) => {
                Object.assign(this._state, { fields, categories, extraFields });
            });
        }
        return this._specificationsProm;
    }

    async createAndSelectCategory({ selectedCategoryKey, createModeKey }) {
        const state = this._state;
        const categoryName = state.newCategoryName.trim();
        if (!categoryName) {
            return;
        }

        const [newCategoryId] = await this.services.orm.create(
            "product.attribute.category",
            [{ name: categoryName }]
        );

        state.categories.push({ id: newCategoryId, name: categoryName });

        state[selectedCategoryKey] = newCategoryId;
        state.newCategoryName = "";
        state[createModeKey] = false;
    }
}

class AddExtraFieldAction extends BuilderAction {
    static id = "addExtraField";
    static dependencies = ["extraFieldsOptionPlugin"];

    setup() {
        // Reload so the server-rendered specifications reflect the database change
        this.reload = {};
    }

    async apply() {
        const state = this.dependencies.extraFieldsOptionPlugin.getState();
        const fieldId = state.fieldId;
        const categoryId = state.categoryId;

        if (!fieldId) {
            return;
        }

        if (state.extraFields.some((extraField) => extraField.field_id[0] === fieldId)) {
            return;
        }

        const websiteId = this.services.website.currentWebsite.id;
        await this.services.orm.create(
            "website.sale.extra.field",
            [{ website_id: websiteId, field_id: fieldId, category_id: categoryId }]
        );
    }
}

class CreateCategoryAction extends BuilderAction {
    static id = "createCategory";
    static dependencies = ["extraFieldsOptionPlugin"];

    async apply() {
        await this.dependencies.extraFieldsOptionPlugin.createAndSelectCategory({
            selectedCategoryKey: "categoryId",
            createModeKey: "categoryCreateMode",
        });
    }
}

class CreateRowCategoryAction extends BuilderAction {
    static id = "createRowCategory";
    static dependencies = ["extraFieldsOptionPlugin"];

    async apply() {
        await this.dependencies.extraFieldsOptionPlugin.createAndSelectCategory({
            selectedCategoryKey: "rowCategoryId",
            createModeKey: "rowCategoryCreateMode",
        });
    }
}

class DeleteExtraFieldAction extends BuilderAction {
    static id = "deleteExtraField";
    static dependencies = ["extraFieldsOptionPlugin"];

    setup() {
        // Reload so the server-rendered specifications reflect the database change
        this.reload = {};
    }

    async apply({ editingElement }) {
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        if (!extraFieldId) {
            return;
        }

        await this.services.orm.unlink("website.sale.extra.field", [extraFieldId]);
    }
}

class ChangeExtraFieldCategoryAction extends BuilderAction {
    static id = "changeExtraFieldCategory";
    static dependencies = ["extraFieldsOptionPlugin"];

    setup() {
        // Reload so the server-rendered specifications reflect the database change
        this.reload = {};
    }

    async apply({ editingElement }) {
        const extraFieldId = parseInt(editingElement.dataset.extraFieldId);
        if (!extraFieldId) return;

        const state = this.dependencies.extraFieldsOptionPlugin.getState();
        if (state.rowCategoryId === null) return;

        await this.services.orm.write(
            "website.sale.extra.field",
            [extraFieldId],
            { category_id: state.rowCategoryId }
        );
    }
}

class SelectExtraFieldAction extends BuilderAction {
    static id = "selectExtraField";
    static dependencies = ["extraFieldsOptionPlugin"];

    isApplied({ value }) {
        return this.dependencies.extraFieldsOptionPlugin.getState().fieldId === value;
    }

    apply({ value }) {
        this.dependencies.extraFieldsOptionPlugin.getState().fieldId = value;
    }
}

class SelectExtraFieldCategoryAction extends BuilderAction {
    static id = "selectExtraFieldCategory";
    static dependencies = ["extraFieldsOptionPlugin"];

    isApplied({ value }) {
        return this.dependencies.extraFieldsOptionPlugin.getState().categoryId === value;
    }

    apply({ value }) {
        this.dependencies.extraFieldsOptionPlugin.getState().categoryId = value;
    }
}

class SetExtraFieldCategoryNameAction extends BuilderAction {
    static id = "setExtraFieldCategoryName";
    static dependencies = ["extraFieldsOptionPlugin"];

    getValue() {
        return this.dependencies.extraFieldsOptionPlugin.getState().newCategoryName;
    }

    apply({ value }) {
        this.dependencies.extraFieldsOptionPlugin.getState().newCategoryName = value || "";
    }
}

class SelectExtraFieldRowCategoryAction extends BuilderAction {
    static id = "selectExtraFieldRowCategory";
    static dependencies = ["extraFieldsOptionPlugin"];

    isApplied({ value }) {
        return this.dependencies.extraFieldsOptionPlugin.getState().rowCategoryId === value;
    }

    apply({ value }) {
        this.dependencies.extraFieldsOptionPlugin.getState().rowCategoryId = value;
    }
}

registry.category("website-plugins").add(ExtraFieldsOptionPlugin.id, ExtraFieldsOptionPlugin);
