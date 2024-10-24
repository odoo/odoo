import options from "@web_editor/js/editor/snippets.options";

options.registry.Disclaimer = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Moves the snippet in #o_snippet_above_header to be common to all pages or inside
     * the first editable oe_structure in the main to be on current page only.
     *
     */
    moveBlock: function (previewMode, widgetValue, params) {
        const snippetEl = this.$target[0].closest('.s_disclaimer');
        let whereEl = null;
        if (widgetValue === 'allPages') {
            whereEl = this.ownerDocument.querySelector('#o_snippet_above_header');
        } else {
            whereEl = this.ownerDocument.querySelector('#wrap');
        }
        whereEl.prepend(snippetEl);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _computeWidgetState: function (methodName, params) {
        switch (methodName) {
            case 'moveBlock':
                return this.$target[0].closest('#o_snippet_above_header') ? 'allPages' : 'currentPage';
        }
        return this._super(...arguments);
    },
});
