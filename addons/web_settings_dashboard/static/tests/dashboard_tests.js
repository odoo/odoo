odoo.define('web_settings_dashboard.dashboard_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var Dashboard = require('web_settings_dashboard');

QUnit.module('Settings', {
    beforeEach: function() {
        var self = this;
        this.data = {
            user: {
                fields: {
                    email: {string: 'Email', type: 'char'},
                },
                records: [
                    {id: 1, email: 'chhagan@odoo.com'},
                    {id: 2, email: 'magan@odoo.com'},
                ]
            },
        };
    }
}, function () {
    QUnit.test('Dashboard: Invite new user', function (assert) {
        assert.expect(2);

        var self = this;
        var dashboardData = {
            'active_users': this.data.user.records.length,
            'pending_counts': 0,
            'pending_users': [],
        };

        var parentDashboard = new Dashboard.Dashboard();
        testUtils.addMockEnvironment(parentDashboard, {
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return $.when({
                        'apps': {},
                        'share': {},
                        'users_info': dashboardData,
                    });
                }
                return this._super(route, args);
            },
        });

        this.invitationsDashboard = new Dashboard.DashboardInvitations(parentDashboard, dashboardData);
        testUtils.addMockEnvironment(this.invitationsDashboard, {
            mockRPC: function (route, args) {
                if (args.method === 'web_dashboard_create_users') {
                    var id = self.data.user.records.length + 1;
                    var email = args['args'][0][0];
                    var user = {'id': id, 'email': email};
                    if (!_.contains(_.pluck(self.data.user.records, 'email'), email)) {
                        dashboardData.active_users++;
                        dashboardData.pending_counts++;
                        dashboardData.pending_users.push(user);
                        self.data.user.records.push(user);
                    }
                    return $.when();
                }
                return this._super(route, args);
            },
        });
        this.invitationsDashboard.appendTo($('#qunit-fixture'));

        var inputBox = this.invitationsDashboard.$el.find('#user_emails');
        var keyPressEvent = $.Event('keypress', {'keyCode': 13});

        inputBox.val('lagan@odoo.com');
        if(inputBox.trigger(keyPressEvent)) {
            this.invitationsDashboard.$el.find('.o_web_settings_dashboard_invitations').trigger('click');
            assert.strictEqual(this.invitationsDashboard.data['pending_counts'], 1, 'New user created');
        }

        // Check for already exist user
        inputBox.val('magan@odoo.com');
        if(inputBox.trigger(keyPressEvent)) {
            this.invitationsDashboard.$el.find('.o_web_settings_dashboard_invitations').trigger('click');
            assert.strictEqual(this.invitationsDashboard.data['pending_counts'], 1, 'User already created');
        }
    });

});

});
