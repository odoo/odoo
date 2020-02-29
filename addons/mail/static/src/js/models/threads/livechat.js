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
     */
    init: function (params) {
        this._super.apply(this, arguments);
        this._name = params.data.correspondent_name;
        this._WEBSITE_USER_NAME = this._name;
    },

    //--------------------------------------------------------------------------
    // Public
    //--------------------------------------------------------------------------

    /**
     * Override so that the list of members has the website use. This is
     * necessary in order for the 'is_typing' feature to compute the name to
     * display of a user that is typing.
     *
     * @override
     * @returns {Promise<Object[]>} resolved with list of list of
     *   livechat members.
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
            return [self._members];
        });
    },
    /**
     * Called when someone starts typing something on the livechat.
     *
     * Overrides it so that it determine the partner based on the received
     * userID. The reason is that anonymous users have the partner ID of the
     * admin, which is likely also an operator, so userID must be used in order
     * to distinct them.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner that is currently
     *   typing something on the thread.
     * @param {boolean} [params.isWebsiteUser=false] whether the typing partner
     *   is an anonymous user (reminder: they share partnerID with admin).
     */
    registerTyping: function (params) {
        params.partnerID = this._WEBSITE_USER_ID;
        this._super.call(this, params);
    },
    /**
     * Called when someone stops typing something on the livechat.
     *
     * Overrides it so that it determine the partner based on the received
     * userID. The reason is that anonymous users have the partner ID of the
     * admin, which is likely also an operator, so userID must be used in order
     * to distinct them.
     *
     * @override {mail.model.ThreadTypingMixin}
     * @param {Object} params
     * @param {integer} params.partnerID ID of the partner that stops typing
     *   something on the thread.
     * @param {boolean} [params.isWebsiteUser=false] whether the typing partner
     *   is an anonymous user (reminder: they share partnerID with admin).
     */
    unregisterTyping: function (params) {
        params.partnerID = this._WEBSITE_USER_ID;
        this._super.call(this, params);
    },
});

return Livechat;

});
