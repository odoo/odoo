odoo.define('partner.UserMenu', function (require) {
"use strict";

var UserMenu = require('web.UserMenu');

var UserMenuLogo = UserMenu.include({
    /**
     * @override
     * @returns {Promise}
     */
    start: function () {
        var self = this;
        var session = this.getSession();
        return this._super.apply(this, arguments).then(function () {
            var $avatar = self.$('.oe_topbar_avatar');
            if (!session.uid) {
                $avatar.attr('src', $avatar.data('default-src'));
                return Promise.resolve();
            }
            var avatar_src = session.url('/web/image', {
                model:'res.users',
                field: 'image_128',
                id: session.uid,
            });
            $avatar.attr('src', avatar_src);
        });
    },

});

});
