/** @odoo-module **/

import publicWidget from '@web/legacy/js/public/public_widget';

publicWidget.registry.searchBar.include({

    /**
     * Allows to keep the invite token and the filters in the URL
     * parameters after clicking on the search bar suggestions.
     *
     * @override
     */
    _render: function (res) {
        if (res && this.searchType === 'appointments' && res.parts.website_url) {
            res.results.forEach(result => {
                result.website_url = `${result.website_url}${location.search}`;
            })
        }
        this._super(...arguments);
    }
});
