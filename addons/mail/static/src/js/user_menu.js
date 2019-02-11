odoo.define('mail.UserMenu', function (require) {
"use strict";

/**
 * This file includes the UserMenu widget defined in Community to add or
 * override actions only available in Enterprise.
 */

var UserMenu = require('web.UserMenu');

UserMenu.include({
    /**
     * @override
     */
    init: function () {
        this._super.apply(this, arguments);
        var session = this.getSession();
        this.outOfOfficeMessage = session.out_of_office_message;
    },
});

});
