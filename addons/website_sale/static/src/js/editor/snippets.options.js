import options from "@web_editor/js/editor/snippets.options";

options.registry.MegaMenuLayout = options.registry.MegaMenuLayout.extend({

    /**
     * Initialize fetchEcomCategories.
     *
     * @returns {void}
     */
    start() {
        this._super();
        this.fetchEcomCategories = this.containerEl.classList.contains('fetchEcomCategories');
    },

    /**
     * Override of `website` to get the e-commerce templates instead of the website's ones.
     *
     * @private
     * @returns {string} xmlid of the current template.
     */
    _getCurrentTemplateXMLID: function () {
        let currentTemplateXMLID = this._super();
        if (this.fetchEcomCategories) {
            currentTemplateXMLID = currentTemplateXMLID.replace('website.', 'website_sale.');
        }
        return currentTemplateXMLID;
    },

    /**
     * Refresh the current mega menu template.
     *
     * @returns {void}
     */
    async refreshMegaMenuTemplate() {
        const xmlid = this._getCurrentTemplateXMLID();
        /*
         * As `selectTemplate` fetch templates from the cache, `_getTemplate` is called first to
         * ensure that the template is in the cache in case users did not open the select before
         * clicking on the checkbox.
         */
        await this._getTemplate(xmlid);
        await this.selectTemplate(true, xmlid);
    },

    /**
     * Toggle the state of the button and refresh the mega menu template.
     *
     * @returns {void}
     */
    async toggleFetchEcomCategories(){
        /**
         * The class applied by `selectClass` in the web editor is applied
         * after calling this method. Therefore, we need to track the
         * changes manually in a variable to ensure that the right template
         * is rendered by `refreshMegaMenuTemplate`.
         */
        this.fetchEcomCategories = !this.fetchEcomCategories;
        await this.refreshMegaMenuTemplate();
    },
});
