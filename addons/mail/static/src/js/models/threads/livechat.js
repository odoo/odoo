odoo.define('mail.model.Livechat', function (require) {
"use strict";

var TwoUserChannel = require('mail.model.TwoUserChannel');

/**
 * backend-side of the livechat.
 *
 * Any piece of code in JS that make use of Livechats must ideally interact with
 * such objects, instead of direct data from the server.
 */
var Livechat = TwoUserChannel.extend({
    _WEBSITE_USER_ID: '_websiteUser',
    _WEBSITE_USER_NAME: 'Website user',

    /**
     * @override
     * @param {Object} params
     * @param {Object} params.data
     * @param {string} params.data.anonymous_name name of the website user
     */
    init: function (params) {
        this._super.apply(this, arguments);

        this._name = params.data.anonymous_name;

        this._WEBSITE_USER_NAME = this._name;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * For the livechat,
     *
     * @override
     * @returns {$.Promise<Object[]>} resolved with list of livechat members
     */
    getMentionPartnerSuggestions: function () {
        var self = this;
        return this._super.apply(this, arguments).then(function () {
            var websiteUser = _.findWhere(self._members, { id: self._WEBSITE_USER_ID });
            if (!websiteUser) {
                self._members.push({
                    id: self._WEBSITE_USER_ID,
                    name: self._WEBSITE_USER_NAME,
                });
            }
            return self._members;
        });
    },
});

return Livechat;

});
