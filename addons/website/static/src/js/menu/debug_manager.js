odoo.define('website.debugManager', function (require) {
'use strict';

var DebugManager = require('web.DebugManager');
var websiteNavbarData = require('website.navbar');

var DebugManagerMenu = websiteNavbarData.WebsiteNavbar.include({
    /**
     * @override
     */
    start: function () {
        if (odoo.debug) {
            new DebugManager(this).prependTo(this.$('.o_menu_systray'));
        }
        return this._super.apply(this, arguments);
    },
});

return DebugManagerMenu;
});
