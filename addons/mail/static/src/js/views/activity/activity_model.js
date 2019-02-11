odoo.define('mail.ActivityModel', function (require) {
'use strict';

var AbstractModel = require('web.AbstractModel');
var session = require('web.session');

var ActivityModel = AbstractModel.extend({
    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
    * @override
    */
    get: function () {
        return this.data;
    },
    /**
     * @override
     * @param {Object} params
     * @param {Array[]} params.domain
     * @returns {Deferred}
     */
    load: function (params) {
        this.domain = params.domain;
        this.modelName = params.modelName;
        this.data = {};
        return this._fetchData();
    },
    /**
     * @param {any} handle
     * @param {Object} params
     * @param {Array[]} params.domain
     * @returns {Deferred}
     */
    reload: function (handle, params) {
        if (params && 'domain' in params) {
            this.domain = params.domain;
        }
        return this._fetchData();
    },

    //--------------------------------------------------------------------------
    // Private
    //--------------------------------------------------------------------------

    /**
     * Fetch activity data.
     *
     * @private
     * @returns {Deferred}
     */
    _fetchData: function () {
        var self = this;
        return this._rpc({
            model: "mail.activity",
            method: 'get_activity_data',
            kwargs: {
                res_model: this.modelName,
                domain: this.domain,
                context: session.user_context,
            }
        }).then(function (result) {
            self.data.data = result;
        });
    },
});

return ActivityModel;

});
