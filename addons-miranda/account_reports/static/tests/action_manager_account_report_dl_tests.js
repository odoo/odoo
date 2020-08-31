odoo.define('account_reports.account_reports_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

var createActionManager = testUtils.createActionManager;

QUnit.module('Account Reports', {
    beforeEach: function () {
        this.actions = [{
            id: 1,
            data: {
                model: 'some_model',
                options: {
                    someOption: true,
                },
                output_format: 'pdf',
            },
            type: 'ir_actions_account_report_download',
        }];
    },
}, function () {

    QUnit.test('can execute account report download actions', async function (assert) {
        assert.expect(4);

        var actionManager = await createActionManager({
            actions: this.actions,
            mockRPC: function (route, args) {
                assert.step(args.method || route);
                return this._super.apply(this, arguments);
            },
            session: {
                get_file: function (params) {
                    assert.step(params.url);
                    assert.deepEqual(params.data, {
                        model: 'some_model',
                        options: {
                            someOption: true,
                        },
                        output_format: 'pdf',
                    }, "should give the correct data");
                    params.success();
                    params.complete();
                },
            },
        });
        await actionManager.doAction(1);

        assert.verifySteps([
            '/web/action/load',
            '/account_reports',
        ]);

        actionManager.destroy();
    });

    QUnit.test('Account report m2m filters', async function (assert) {
        assert.expect(4);
        var count = 0;
        var actionManager = await createActionManager({
            actions: [{
                id: 9,
                tag: 'account_report',
                type: 'ir.actions.client',
            }],
            data: {
                'res.partner.category': {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                    },
                    records: [{
                        id: 1,
                        display_name: "Brigadier suryadev singh",
                    }],
                },
                'res.partner': {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        partner_ids: {string: "Partner", type: "many2many", relation: 'partner'},
                    },
                    records: [{
                        id: 1,
                        display_name: "Genda Swami",
                        partner_ids: [1],
                    }]
                },
            },
            mockRPC: function (route, args) {
                if (route === '/web/dataset/call_kw/account.report/get_report_informations') {
                    var vals = {
                        options: {partner: true, partner_ids: [], partner_categories:[]},
                        buttons: [],
                        searchview_html: '<a class="dropdown-toggle" data-toggle="dropdown">' +
                            '<span class="fa fa-folder-open"/> Partners' +
                            '<span class="caret" />' +
                            '</a>' +
                            '<ul class="dropdown-menu o_filters_menu" role="menu">' +
                            '<li class="o_account_report_search js_account_partner_m2m"/>' +
                            '</ul>',
                    };
                    var reportOptions;
                    if (count === 1) {
                        reportOptions = args.args[1];
                        assert.strictEqual(reportOptions.partner_ids[0], 1,
                            "pass correct partner_id to report");
                        vals.options.partner_ids = reportOptions.partner_ids;
                    } else if (count == 2) {
                        reportOptions = args.args[1];
                        assert.strictEqual(reportOptions.partner_categories[0], 1,
                            "pass correct partner_id to report");
                        vals.options.partner_categories = reportOptions.partner_categories;
                    }
                    count++;
                    return Promise.resolve(vals);
                }
                if (route === '/web/dataset/call_kw/account.report/get_html_footnotes') {
                    return Promise.resolve("");
                }
                return this._super.apply(this, arguments);
            },
        });

        await actionManager.doAction(9);
        assert.containsOnce(actionManager, '.o_control_panel .o_field_many2manytags[name="partner_ids"]',
            "partner_ids m2m field added to filter");

        // search on partners m2m
        await testUtils.dom.click(actionManager.$('.o_control_panel .o_search_options a.dropdown-toggle'));
        await testUtils.fields.many2one.clickOpenDropdown('partner_ids');
        await testUtils.nextTick();
        await testUtils.fields.many2one.clickItem('partner_ids', 'Genda Swami');
        await testUtils.nextTick();

        assert.containsOnce(actionManager, '.o_control_panel .o_field_many2manytags[name="partner_categories"]',
            "partner_categories m2m field added to filter");

        // search on partner categories m2m
        await testUtils.dom.click(actionManager.$('.o_control_panel .o_search_options a.dropdown-toggle'));
        await testUtils.nextTick();
        await testUtils.fields.many2one.clickOpenDropdown('partner_categories');
        await testUtils.nextTick();
        await testUtils.fields.many2one.clickItem('partner_categories', 'Brigadier suryadev singh');
        await testUtils.nextTick();

        actionManager.destroy();
    });
});

});
