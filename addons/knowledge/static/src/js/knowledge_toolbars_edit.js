/** @odoo-module */

import { KnowledgeToolbar } from './knowledge_toolbars';

/**
 * @see KnowledgeToolbar
 * This override is loaded as an asset of web_editor to access editor methods
 * and utils.
 */
KnowledgeToolbar.include({
    /**
     * set the toolbar anchor as non-editable
     *
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.editor.observerUnactive('knowledge_toolbar_uneditable');
            this.anchor.setAttribute('contenteditable', 'false');
            this.editor.observerActive('knowledge_toolbar_uneditable');
        }
    },
    /**
     * @override
     */
    removeToolbar: function () {
        if (this.mode === 'edit') {
            this.editor.observerUnactive();
        }
        this._super.apply(this, arguments);
        if (this.mode === 'edit') {
            this.editor.observerActive();
        }
    },
});
