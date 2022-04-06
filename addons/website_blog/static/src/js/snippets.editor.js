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
        // TODO: adapt in master - add missing "data-no-check" on blog tag option.
        const blogPostTagOptionEl = $html.find('[data-js="BlogPostTagSelection"]')[0];
        if (blogPostTagOptionEl) {
            blogPostTagOptionEl.dataset.noCheck = true;
        }
    },
});
