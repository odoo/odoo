/** @odoo-module */
import { registry } from "@web/core/registry";
import { Base } from "./related_models";

export class PosCategory extends Base {
    static pythonModel = "pos.category";

    getAllChildren(category) {
        const children = [];

        if (!category) {
            category = this;
        }

        if (category.child_id.length === 0) {
            return children;
        }

        for (const child of category.child_id) {
            children.push(child.id);

            if (child.child_id.length > 0) {
                children.push(...this.getAllChildren(child));
            }
        }

        return children;
    }

    get allParents() {
        const parents = [];
        let parent = this.parent_id;

        if (!parent) {
            return parents;
        }

        while (parent) {
            parents.unshift(parent);
            parent = parent.parent_id;
        }

        return parents.reverse();
    }
}

registry.category("pos_available_models").add(PosCategory.pythonModel, PosCategory);
