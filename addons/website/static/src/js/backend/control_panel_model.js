odoo.define('website.ControlPanelModel', function (require) {
"use strict";

var Domain = require('web.Domain');
var controlPanelModel = require('web.ControlPanelModel');

var websiteControlPanelModel = controlPanelModel.include({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     */
    get: function () {
        var dict = this._super.apply(this, arguments);
        dict.websites = this.websites;
        return dict;
    },
    /**
     * @override
     * @param {string} filterId
     */
    toggleFilter: function (filterId) {
        var filter = this.filters[filterId];
        var index = this.index;
        if (index === -1) {
            if (filter.type === 'website') {
                var websiteFilters = _.filter(this.filters, function (filter) {
                    return filter.type === 'website';
                });
                var toRemove = websiteFilters[websiteFilters.length - 2];
                if (toRemove && _.contains(this.query, toRemove.groupId)) {
                    this.query.splice(this.query.indexOf(toRemove.groupId), 1);
                }
            }
        }
        this._super.apply(this, arguments);
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * @private
     */
    _getFilterDomain: function (filter) {
        let domain;
        if (filter.type === 'website') {
            domain = filter.domain;
            if (filter.domain === undefined) {
                domain = Domain.prototype.constructDomain(
                    filter.fieldName,
                    filter.currentOptionId,
                    filter.fieldType
                );
            }
            return domain;
        }
        return this._super.apply(this, arguments);
    },
});

return websiteControlPanelModel;

});
