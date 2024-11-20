import options from "@web_editor/js/editor/snippets.options";


/**
 * Manage the visibility of snippets on mobile/desktop.
 */
options.registry.CrashSnippet = options.Class.extend({

    //--------------------------------------------------------------------------
    // Options
    //--------------------------------------------------------------------------

    /**
     * Raise an error if the crash button is clicked.
     *
     * @see this.selectClass for parameters
     */
    async crashSnippet(previewMode, widgetValue, params) {
        throw new Error('This option is made to raise an error.')
    },

});