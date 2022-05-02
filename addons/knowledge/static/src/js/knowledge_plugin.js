/** @odoo-module */

/**
 * Plugin for OdooEditor. Allow to remove temporary toolbars content which are
 * not destined to be stored in the field_html
 */
export class KnowledgePlugin {
    /**
     * @param {Element} editable
     */
    cleanForSave(editable) {
        for (const node of editable.querySelectorAll('.o_knowledge_toolbar_anchor')) {
            if (node.oKnowledgeToolbar) {
                node.oKnowledgeToolbar.removeToolbar();
            }
            while (node.firstChild) {
                node.removeChild(node.lastChild);
            }
        }
        for (const node of editable.querySelectorAll('.o_knowledge_behavior_anchor')) {
            if (node.oKnowledgeBehavior) {
                node.oKnowledgeBehavior.removeBehavior();
            }
        }
    }
}
