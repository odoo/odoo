/** @odoo-module **/

import snippetEditor from 'web_editor.snippet.editor';

snippetEditor.SnippetsMenu.include({

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _patchForComputeSnippetTemplates: function ($html) {
        this._super(...arguments);
        // TODO: remove in master.
        const blogPostTagOptionEl = $html.find('[data-js="BlogPostTagSelection"]')[0];
        if (blogPostTagOptionEl) {
            blogPostTagOptionEl.dataset.noCheck = true;
        }
    },
});
