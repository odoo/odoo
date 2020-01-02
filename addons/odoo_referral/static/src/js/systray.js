odoo.define('systray.systray_odoo_referral', function(require) {
    "use strict";
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var ActionMenu = Widget.extend({
        template: 'systray_odoo_referral.gift_icon',
        events: {
            'click .gift_icon': 'onclick_gifticon',
        },
        start:function(parent) {
            var self = this;
            this._rpc({
                model: 'res.users',
                method: 'get_referral_updates_count_for_current_user'
            }).then(function (result) {
                if(result > 0) {
                    self.$('.o_notification_counter').text(result);
                }
            });
            return this._super.apply(this, arguments);
        },
        onclick_gifticon:function(){
            var self = this;
            this._rpc({
                route:'/referral/go/'
            }).then(function (result) {
                self.$('.o_notification_counter').text(0);
                window.open(result.link);
            });
        },
    });

    SystrayMenu.Items.push(ActionMenu);
    return ActionMenu;
});
