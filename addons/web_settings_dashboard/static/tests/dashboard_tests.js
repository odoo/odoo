odoo.define('web_settings_dashboard.dashboard_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Dashboard = require('web_settings_dashboard');
var Widget = require('web.Widget');

QUnit.module('Settings', {
    beforeEach: function() {
        this.dashboardData = {
            'active_users': 1,
            'pending_counts': 1,
            'pending_users': [{'id': 1, 'email': 'xyz@odoo.com'}],
        };
    }
}, function () {
    QUnit.test('Dashboard: Invite new user', function (assert) {
        assert.expect(1);
        var self = this;

        var parentDashboard = new Dashboard.Dashboard();
        testUtils.addMockEnvironment(parentDashboard, {
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return $.when({
                        'apps': {},
                        'share': {},
                        'users_info': self.dashboardData,
                    });
                }
                return this._super(route, args);
            },
        });

        var invitationsDashboard = new Dashboard.DashboardInvitations(parentDashboard, this.dashboardData);
        testUtils.addMockEnvironment(invitationsDashboard, {
            mockRPC: function (route, args) {
                if (args.method === 'web_dashboard_create_users') {
                    self.dashboardData.active_users++;
                    self.dashboardData.pending_counts++;
                    self.dashboardData.pending_users.push({'id': 2, 'email': args['args'][0][0]});
                    return $.when();
                }
                return this._super(route, args);
            },
        });
        invitationsDashboard.appendTo($('#qunit-fixture'));

        var inputBox = invitationsDashboard.$el.find('#user_emails').val('abc@odoo.com');
        var keyPressEvent = $.Event('keypress', {'keyCode': 13});
        if(inputBox.trigger(keyPressEvent)) {
            invitationsDashboard.$el.find('.o_web_settings_dashboard_invitations').trigger('click');
            assert.strictEqual(invitationsDashboard.data['pending_users'].length, 2, 'New user created');
        }
    });

});

});
