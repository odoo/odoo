odoo.define('systray.systray_odoo_referral', function (require) {
    "use strict";
    var core = require('web.core');
    var localStorage = require('web.local_storage');
    var SystrayMenu = require('web.SystrayMenu');
    var Widget = require('web.Widget');

    var _t = core._t;
    var ActionMenu = Widget.extend({
        template: 'systray_odoo_referral.gift_icon',
        events: {
            'click .gift_icon': 'onclick_gifticon',
        },

        start: function (parent) {
            var self = this;
            var lastFetch = localStorage.getItem('odoo_referral.updates_last_fetch');
            var updatesCount = localStorage.getItem('odoo_referral.updates_count');
            var hasClicked = localStorage.getItem('odoo_referral.has_clicked');
            if (hasClicked && (!lastFetch || Date(parseInt(lastFetch)) < Date(new Date().getTime() - (24 * 60 * 60 * 1000)))) {
                this._rpc({
                    model: 'res.users',
                    method: 'get_referral_updates_count_for_current_user'
                }, {
                    shadow: true,
                }).then(function (count) {
                    localStorage.setItem('odoo_referral.updates_last_fetch', Date.now());
                    localStorage.setItem('odoo_referral.updates_count', count);
                    if (count > 0) {
                        self.$('.o_notification_counter').text(count);
                    }
                });
            } else {
                if (updatesCount && updatesCount > 0) {
                    self.$('.o_notification_counter').text(updatesCount);
                }
            }
            return this._super.apply(this, arguments);
        },

        onclick_gifticon: function () {
            var self = this;
            localStorage.setItem('odoo_referral.updates_count', 0);
            this._rpc({
                route: '/odoo_referral/go/'
            }).then(function (result) {
                localStorage.setItem('odoo_referral.has_clicked', 1);
                self.$('.o_notification_counter').text('');
                var w = window.open(result.link, '_blank', 'noreferrer noopener');
                if (!w || w.closed || typeof w.closed === 'undefined') {
                    var message = _t('A popup window has been blocked. You ' +
                                 'may need to change your browser settings to allow ' +
                                 'popup windows for this page.');
                    self.do_warn(_t('Warning'), message, true);
                }
            });
        },
    });

    SystrayMenu.Items.push(ActionMenu);
    return ActionMenu;
});
