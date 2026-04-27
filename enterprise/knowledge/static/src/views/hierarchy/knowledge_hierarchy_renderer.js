/** @odoo-module */

import { HierarchyRenderer } from "@web_hierarchy/hierarchy_renderer";
import { KnowledgeHierarchyCard } from "@knowledge/views/hierarchy/knowledge_hierarchy_card";

export class KnowledgeHierarchyRenderer extends HierarchyRenderer {
    static components = {
        ...HierarchyRenderer.components,
        HierarchyCard: KnowledgeHierarchyCard,
    }
}
