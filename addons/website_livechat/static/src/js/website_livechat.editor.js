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

    /**
     * @private
     */
    _createNewChannel: function () {
        var self = this;
        wUtils.prompt({
            window_title: _t("New Channel"),
            input: _t("Name"),
        }).then(function (name) {
            self._rpc({
                route: '/livechat/add_channel',
                params: {
                    name: name,
                },
            }).then(function (url) {
                window.location.href = url;
            });
        });
    },
});

});
