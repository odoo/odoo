odoo.define('web_settings_dashboard.settings_dashboard_tests', function (require) {
"use strict";

var webSettingsDashboard = require('web_settings_dashboard');

var testUtils = require('web.test_utils');
var Widget = require('web.Widget');

var Dashboard = webSettingsDashboard.Dashboard;

function createDashboard(params) {
    var widget = new Widget();
    var dashboard = new Dashboard(widget);
    dashboard.all_dashboards = params.dashboards || ['invitations']; // test only user invitations

    testUtils.addMockEnvironment(widget, params);

    var originalDestroy = Dashboard.prototype.destroy;
    dashboard.destroy = function () {
        dashboard.destroy = originalDestroy;
        widget.destroy();
    };

    dashboard.appendTo($('#qunit-fixture'));

    return dashboard;
}

QUnit.module('settings dashboard', function () {

    QUnit.test('Dashboard Planners should show translated name of apps', function (assert) {
        assert.expect(1);

        var data = {
            'web.planner': {
                fields: {
                    name: {string: "Name", type: "char" },
                    menu_id: {string: "Menu", type: "many2one",  relation: 'menu'},
                    data: {string: "Data", type: "char" },
                },
                records: [
                    {id:1, name: 'accounting', menu_id: 1, data: false},
                ],
            },

            menu: {
                fields: {
                    name: {string: "Name", type: "char"},
                },
                records: [
                    {id:1, name: 'accounting'},
                ],
            }
        }

        var dashboard = createDashboard({
            data: data,
            dashboards: ['planner'],
            mockRPC: function (route, args) {
                if (route === '/web_settings_dashboard/data') {
                    return $.when({});
                }
                if (route === '/web/dataset/call_kw/web.planner/search_read') {
                    assert.deepEqual(args.kwargs.context, {lang: 'fr_BE'},
                        'The language should have been passed');
                }
                return this._super.apply(this, arguments);
            },
            session: {
                user_context: {lang: 'fr_BE'},
            },
        });

        dashboard.destroy();
    });
});
});
