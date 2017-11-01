odoo.define('web_settings_dashboard.settings_dashboard_tests', function (require) {
"use strict";

var Dashboard = require('web_settings_dashboard');
var testUtils = require('web.test_utils');

QUnit.module('settings_dashboard', {
    beforeEach: function () {
        this.data = {
            user: {
                records: [{
                    id: 1,
                    email: 'chhagan@odoo.com'
                }, {
                    id: 2,
                    email: 'magan@odoo.com'
                }],
            },
        };
    }
}, function () {
    QUnit.test('Dashboard: Invite new user', function (assert) {
        assert.expect(3);

        var self = this;
        var dashboardData = {
            'active_users': this.data.user.records.length,
            'pending_counts': 0,
            'pending_users': [],
        };
        var dashboard = new Dashboard.Dashboard();
        dashboard.all_dashboards = ['invitations']; // test only user invitations

        testUtils.addMockEnvironment(dashboard, {
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return $.when({
                        'share': {},
                        'users_info': dashboardData,
                    });
                }
                if (route === '/web/dataset/call_kw/res.users/web_dashboard_create_users') {
                    var id = self.data.user.records.length + 1;
                    var email = args['args'][0][0];
                    var user = [id, email];
                    dashboardData.pending_counts++;
                    dashboardData.pending_users.push(user);
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
        });
        dashboard.appendTo($('#qunit-fixture'));

        // Add email to invite
        var $userEmails = dashboard.$('#user_emails');
        $userEmails.text('lagan@odoo.com').trigger($.Event('keydown', {keyCode: $.ui.keyCode.ENTER}));
        assert.strictEqual(dashboard.$('.o_badge_text').text().trim(), 'lagan@odoo.com',
            'Invite new users should have badge with provided email');

        // Send invitation
        dashboard.$('.o_web_settings_dashboard_invite').click();
        assert.strictEqual(dashboardData.pending_counts, 1,
            'After click invite, email should be in pending state');
        assert.strictEqual(dashboard.$('.o_web_settings_dashboard_user').text().trim(), 'lagan@odoo.com',
            'After click invite, email badge should be in pending invitations');

        dashboard.destroy();
    });
});

});
