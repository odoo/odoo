odoo.define('awesome_map.MapModel', function (require) {
"use strict";

var AbstractModel = require('web.AbstractModel');

var MapModel = AbstractModel.extend({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        this.data = null;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * @override
     * @returns {Object}
     */
    get: function () {
        return this.data;
    },

    /**
     * @override
     * @param {Object} params
     * @returns {Deferred}
     */
    load: function (params) {
        var self = this;
        var fields = [params.latitudeField, params.longitudeField];
        return this._rpc({
            model: params.modelName,
            method: 'search_read',
            context: params.context,
            fields: fields,
            domain: params.domain
        }).then(function (results) {
            self.data = _.map(results, function (result) {
                return {
                    id: result.id,
                    latitude: result[params.latitudeField],
                    longitude: result[params.longitudeField],
                };
            });
        });
    },
});

return MapModel;

});