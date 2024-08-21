import options from "@web_editor/js/editor/snippets.options";

options.registry.MegaMenuLayout = options.registry.MegaMenuLayout.extend({
    _fetchEcommerceCategories() {
        return this.containerEl.classList.contains('fetchEcomCategories');
    },

    /**
     * Override of `website` to get the e-commerce templates instead of the website's ones.
     *
     * @private
     * @returns {string} xmlid of the current template.
     */
    _getCurrentTemplateXMLID: function () {
        let currentTemplateXMLID = this._super();
        if (this._fetchEcommerceCategories()) {
            currentTemplateXMLID = currentTemplateXMLID.replace('website.', 'website_sale.');
        }
        return currentTemplateXMLID;
    },

    /**
     * Refresh the current mega menu template.
     *
     * @private
     * @returns {void} xmlid of the current template.
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
});
