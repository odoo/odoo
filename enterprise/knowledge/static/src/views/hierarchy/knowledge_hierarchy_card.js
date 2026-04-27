/** @odoo-module */

import { HierarchyCard } from "@web_hierarchy/hierarchy_card";

export class KnowledgeHierarchyCard extends HierarchyCard {
    /**
     * @override
     * Add a context variable to be able to show/hide the section if a node
     * is a root (in the hierarchy view).
     */
    getRenderingContext(data) {
        const context = super.getRenderingContext(data);
        return {
            ...context,
            isRoot: !this.props.node.parentNode,
        };
    }
}
