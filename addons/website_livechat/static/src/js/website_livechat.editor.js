odoo.define('website_livechat.editor', function (require) {
'use strict';

var core = require('web.core');
var wUtils = require('website.utils');
var WebsiteNewMenu = require('website.newMenu');

var _t = core._t;

WebsiteNewMenu.include({
    actions: _.extend({}, WebsiteNewMenu.prototype.actions || {}, {
        new_channel: '_createNewChannel',
    }),

    //--------------------------------------------------------------------------
    // Actions
    //--------------------------------------------------------------------------

    /**
     * Asks the user information about a new channel to create, then creates it
     * and redirects the user to this new channel.
     *
     * @private
     * @returns {Promise} Unresolved if there is a redirection
     */
    _createNewChannel: function () {
        var self = this;
        return wUtils.prompt({
            window_title: _t("New Channel"),
            input: _t("Name"),
        }).then(function (result) {
            var name = result.val;
            if (!name) {
                return;
            }
            return self._rpc({
                model: 'im_livechat.channel',
                method: 'create_and_get_website_url',
                args: [[]],
                kwargs: {
                    name: name,
                },
            }).then(function (url) {
                window.location.href = url;
                return new Promise(function () {});
            });
        });
    },
});

});
