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
        for (const node of editable.querySelectorAll('.o_knowledge_toggle')) {
            const toggleContent = node.querySelector('.o_knowledge_toggle_content');
            toggleContent.classList.add('d-none');
            const caret = node.querySelector('.o_toggle_caret').firstElementChild;
            caret.classList.remove('fa-caret-square-o-down');
            caret.classList.add('fa-caret-square-o-right');
        }
    }
    /**
     * @param {Element} editable
     */
    cleanForPaste(editable) {
        if (editable.querySelectorAll) {
            // remove ID from toggle elements
            for (const node of editable.querySelectorAll('.o_knowledge_toggle')) {
                node.removeAttribute('id');
            }
        }
    }
}
