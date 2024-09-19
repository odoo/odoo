import options from "@web_editor/js/editor/snippets.options";

options.registry.MegaMenuLayout = options.registry.MegaMenuLayout.extend({
    _fetchECommerceCategories() {
        return this.containerEl.classList.contains('fetchEComCategories');
    },

    /**
     * Override of `website` TODO VCR...
     * Retrieves a template either from cache or through RPC.
     *
     * @private
     * @param {string} xmlid
     * @returns {string}
     */
    async _getTemplate(xmlid) {
        if (this._fetchECommerceCategories()) {
            xmlid.replace('website.', 'website_sale.');
        }
        return this._super(xmlid);
    },
});
