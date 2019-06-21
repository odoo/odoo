odoo.define('website.debugManager', function (require) {
'use strict';

var config = require('web.config');
var DebugManager = require('web.DebugManager');
var websiteNavbarData = require('website.navbar');

var DebugManagerMenu = websiteNavbarData.WebsiteNavbar.include({
    /**
     * @override
     */
    start: function () {
        if (config.isDebug()) {
            new DebugManager(this).prependTo(this.$('.o_menu_systray'));
        }
        return this._super.apply(this, arguments);
    },
});

return DebugManagerMenu;
});
