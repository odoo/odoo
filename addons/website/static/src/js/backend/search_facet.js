odoo.define('website.SearchFacet', function (require) {
"use strict";

var searchFacet = require('web.SearchFacet');

var websiteSearchFacet = searchFacet.include({
    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    _getIcon: function () {
        this.icon = 'fa-globe';
        return this._super.apply(this, arguments);
    },
});

return websiteSearchFacet;

});
