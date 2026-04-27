/** @odoo-module */

import { HierarchyModel } from "@web_hierarchy/hierarchy_model";

export class KnowledgeHierarchyModel extends HierarchyModel {
    /**
     * @override
     * Use the `move_to` method of the model instead of a simple `write` for
     * some extra processing and validations.
     */
    async updateParentId(node, parentResId = false) {
        return this.orm.call("knowledge.article", "move_to", [node.resId], {
            parent_id: parentResId,
            category: parentResId ? false : node.data.category,
        });
    }
}
