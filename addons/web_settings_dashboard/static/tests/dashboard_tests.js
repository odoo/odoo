odoo.define('web_settings_dashboard.settings_dashboard_tests', function (require) {
"use strict";

var webSettingsDashboard = require('web_settings_dashboard');
var NotificationService = require('web.NotificationService');
var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var Dashboard = webSettingsDashboard.Dashboard;

async function createDashboard (params) {
    var widget = new Widget();
    // action content not used in tests apparently
    var action = {};
    var dashboard = new Dashboard(widget, action);
    dashboard.all_dashboards = params.dashboards || ['invitations']; // test only user invitations

    testUtils.mock.addMockEnvironment(widget, params);

    var originalDestroy = Dashboard.prototype.destroy;
    dashboard.destroy = function () {
        dashboard.destroy = originalDestroy;
        widget.destroy();
    };

    var target = params.debug ? $('body') : $('#qunit-fixture');
    await dashboard.appendTo(target);

    return dashboard;
}

QUnit.module('settings_dashboard', function () {
    QUnit.test('Dashboard: Invite new user', async function (assert) {
        assert.expect(4);

        var dashboardData = {
            active_users: 4,
            pending_counts: 0,
            pending_users: [],
        };
        var dashboard = await createDashboard({
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve({
                        share: {},
                        users_info: dashboardData,
                    });
                }
                if (route === '/web/dataset/call_kw/res.users/web_dashboard_create_users') {
                    dashboardData.pending_counts++;
                    dashboardData.pending_users.push([5, args.args[0][0]]);
                    return Promise.resolve(true);
                }
                return this._super.apply(this, arguments);
            },
        });

        // add email to invite
        await testUtils.fields.editInput(dashboard.$('.o_user_emails'), 'lagan@odoo.com');
        await testUtils.fields.triggerKeydown(dashboard.$('.o_user_emails'), 'enter');
        assert.strictEqual(dashboard.$('.o_badge_text').text().trim(), 'lagan@odoo.com',
            'should generate a badge with provided email');
        assert.strictEqual(dashboard.$('.o_user_emails').val(), '',
            'input should have been cleared');

        // send invitation
        await testUtils.dom.click(dashboard.$('.o_web_settings_dashboard_invite'));
        assert.strictEqual(dashboard.$('.o_web_settings_dashboard_user').text().trim(), 'lagan@odoo.com',
            'should have created a badge in pending invitations');
        assert.containsNone(dashboard, '.o_badge_text',
            'should have removed the badge from the invite area');

        dashboard.destroy();
    });

    QUnit.test('Dashboard: Invite new user (warnings)', async function (assert) {
        assert.expect(8);

        var dashboard = await createDashboard({
            mockRPC: function (route) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve({
                        share: {},
                        users_info: {
                            active_users: 4,
                            pending_counts: 1,
                            pending_users: [[3, 'xyz@odoo.com']],
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        assert.step(params.type);
                    }
                }),
            },
        });

        // enter an invalid email address to invite
        await testUtils.fields.editInput(dashboard.$('.o_user_emails'), 'x@y');
        await testUtils.fields.triggerKeydown(dashboard.$('.o_user_emails'), 'enter');
        assert.containsNone(dashboard, '.o_badge_text',
            'should not have generated any badge');
        assert.strictEqual(dashboard.$('.o_user_emails').val(), 'x@y',
            'input should not have been cleared');
        assert.verifySteps(['danger']);

        // enter an already pending address
        await testUtils.fields.editInput(dashboard.$('.o_user_emails'), 'xyz@odoo.com');
        await testUtils.fields.triggerKeydown(dashboard.$('.o_user_emails'), 'enter');
        assert.containsNone(dashboard, '.o_badge_text',
            'should not have generated any badge');
        assert.strictEqual(dashboard.$('.o_user_emails').val(), 'xyz@odoo.com',
            'input should not have been cleared');
        assert.verifySteps(['danger']);

        dashboard.destroy();
    });

    QUnit.test('Dashboard: Invite a list of users', async function (assert) {
        assert.expect(2);

        var dashboard = await createDashboard({
            mockRPC: function (route) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve({
                        share: {},
                        users_info: {
                            active_users: 4,
                            pending_counts: 1,
                            pending_users: [],
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        // simulate a copy paste of multiple email addresses
        var emails = ['a@odoo.com', 'b@odoo.com', 'c@odoo.com', 'd@odoo.com'];
        await testUtils.fields.editInput(dashboard.$('.o_user_emails'), emails.join(' '));
        await testUtils.fields.triggerKeydown(dashboard.$('.o_user_emails'), 'enter');
        assert.containsN(dashboard, '.o_badge_text', 4,
            'should have generated 4 badges');
        assert.strictEqual(dashboard.$('.o_user_emails').val(), '',
            'input have been cleared');

        dashboard.destroy();
    });

    QUnit.test('Dashboard: Invite a list of users (with warnings)', async function (assert) {
        assert.expect(5);

        var dashboard = await createDashboard({
            mockRPC: function (route) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve({
                        share: {},
                        users_info: {
                            active_users: 4,
                            pending_counts: 1,
                            pending_users: [[4, 'a@odoo.com'], [5, 'd@odoo.com']],
                        },
                    });
                }
                return this._super.apply(this, arguments);
            },
            services: {
                notification: NotificationService.extend({
                    notify: function (params) {
                        assert.step(params.type);
                    }
                }),
            },
        });

        // simulate a copy paste of multiple email addresses
        var emails = ['a@odoo.com', 'b@odoo.com', 'x@y', 'd@odoo.com'];
        await testUtils.fields.editInput(dashboard.$('.o_user_emails'), emails.join(' '));
        await testUtils.fields.triggerKeydown(dashboard.$('.o_user_emails'), 'enter');
        assert.containsOnce(dashboard, '.o_badge_text',
            'should have generated 1 badge');
        assert.strictEqual(dashboard.$('.o_user_emails').val(), '',
            'input have been cleared');
        assert.verifySteps(['danger', 'danger'], "should have triggered 2 warnings");

        dashboard.destroy();
    });

    QUnit.test('Prevent default behaviour when clicking on load translation', async function (assert) {
        assert.expect(3);

        var dashboard = await createDashboard({
            dashboards: ['translations'],
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve();
                }
                return this._super.apply(this, arguments);
            },
        });

        var $loadTranslation = dashboard.$('.o_load_translations');

        assert.strictEqual($loadTranslation.length, 1,
            "should have button to load translations");

        // Prevent the browser default behaviour when clicking on anything.
        // This includes clicking on a `<a>` with `href`, so that it does not
        // change the URL in the address bar.
        $(document.body).on('click.o_test', function (ev) {
            assert.ok(ev.isDefaultPrevented(),
                "should have prevented browser default behaviour");
            assert.strictEqual(ev.target, $loadTranslation[0],
                "should have clicked on 'load a translation' button");
            ev.preventDefault();
        });

        await testUtils.dom.click($loadTranslation);

        $(document.body).off('click.o_test');

        dashboard.destroy();
    });

    QUnit.test('Prevent default behaviour when clicking on set up company', async function (assert) {
        assert.expect(3);

        var dashboard = await createDashboard({
            dashboards: ['company'],
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve({
                        company: {
                            company_name: 'MyCompany'
                        }
                    });
                }
                return this._super.apply(this, arguments);
            },
        });

        var $setupCompany = dashboard.$('.o_setup_company');

        assert.strictEqual($setupCompany.length, 1,
            "should have button to set up company");

        // Prevent the browser default behaviour when clicking on anything.
        // This includes clicking on a `<a>` with `href`, so that it does not
        // change the URL in the address bar.
        $(document.body).on('click.o_test', function (ev) {
            assert.ok(ev.isDefaultPrevented(),
                "should have prevented browser default behaviour");
            assert.strictEqual(ev.target, $setupCompany[0],
                "should have clicked on 'setup company' button");
            ev.preventDefault();
        });

        await testUtils.dom.click($setupCompany);

        $(document.body).off('click.o_test');

        dashboard.destroy();
    });

    QUnit.test('Prevent default behaviour when clicking on browse apps', async function (assert) {
        assert.expect(3);

        var dashboard = await createDashboard({
            dashboards: ['apps'],
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return Promise.resolve({
                        apps: {},
                    });
                }
                if (args.method === 'get_account_url') {
                    return Promise.resolve('fakeURL');
                }
                return this._super.apply(this, arguments);
            },
        });

        var $browseAppsButton = dashboard.$('.btn.o_browse_apps');

        // Prevent the browser default behaviour when clicking on anything.
        // This includes clicking on a `<a>` with `href`, so that it does not
        // change the URL in the address bar.
        $(document.body).on('click.o_test', function (ev) {
            assert.ok(ev.isDefaultPrevented(),
                "should have prevented browser default behaviour");
            assert.strictEqual(ev.target, $browseAppsButton[0],
                "should have clicked on 'browse apps' button");
            ev.preventDefault();
        });

        assert.strictEqual($browseAppsButton.length, 1,
            "should have button to browse apps");

        await testUtils.dom.click($browseAppsButton);

        $(document.body).off('click.o_test');
        dashboard.destroy();
    });
});

});
