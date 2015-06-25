odoo.define('web.SwitchCompany', function(require) {
    "use strict";

var core = require('web.core');
var Model = require('web.Model');
var web_client = require('web.web_client');
var session = require('web.session');
var SystrayMenu = require('web.SystrayMenu');
var Widget = require('web.Widget');

var _t = core._t;

var SwitchCompany = Widget.extend({
    template: 'SwitchCompany',
    start: function() {
        var self = this;
        new Model('res.users').call('user_systray_info').then(function(res) {
            if (res.company) {
                self.$el.removeClass("hidden").on('click', function(ev) {
                    ev.preventDefault();
                    self.switch_user_company();
                }).tooltip({
                    title: function() {
                        return _.str.sprintf(_t("<center>Click here to switch company.<br/>Your current company is <strong>%s</strong>.</center>"), res.company);
                    },
                });
            }
        });
        return this._super.apply(this, arguments);
    },
    switch_user_company: function() {
        var self = this;
        web_client.clear_uncommitted_changes().then(function() {
            self.rpc("/web/action/load", {
                action_id: "base.action_res_users_comp_switch"
            }).done(function(result) {
                result.res_id = session.uid;
                web_client.action_manager.do_action(result);
            });
        });
    },
});

// Put SwitchCompany widget in the systray menu.
SystrayMenu.Items.push(SwitchCompany);

});
