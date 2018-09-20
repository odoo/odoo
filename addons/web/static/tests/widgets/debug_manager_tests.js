odoo.define('web.debugManagerTests', function (require) {
"use strict";

var DebugManager = require('web.DebugManager');
var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

/**
 * Create and return an instance of DebugManager with all rpcs going through a
 * mock method, assuming that the user has access rights, and is an admin.
 *
 * @param {Object} [params={}]
 */
var createDebugManager = function (params) {
    params = params || {};
    var mockRPC = params.mockRPC;
    _.extend(params, {
        mockRPC: function (route, args) {
            if (args.method === 'check_access_rights') {
                return $.when(true);
            }
            if (args.method === 'xmlid_to_res_id') {
                return $.when(true);
            }
            if (mockRPC) {
                return mockRPC.apply(this, arguments);
            }
            return this._super.apply(this, arguments);
        },
        session: {
            user_has_group: function (group) {
                if (group === 'base.group_no_one') {
                    return $.when(true);
                }
                return this._super.apply(this, arguments);
            },
        },
    });
    var debugManager = new DebugManager();
    testUtils.addMockEnvironment(debugManager, params);
    return debugManager;
};

QUnit.module('DebugManager', {}, function () {

    QUnit.test("edit view menu item", function (assert) {
        assert.expect(3);

        var debugManager = createDebugManager();

        debugManager.appendTo($('#qunit-fixture'));

        // Simulate update debug manager from web client
        var action = {
            views: [{
                fieldsView: {
                    view_id: 1,
                },
                type: "list",
            }],
        };
        var view = {
            viewType: "list",
        };
        debugManager.update('action', action, view);

        var $editView = debugManager.$('a[data-action=edit][data-model="ir.ui.view"]');
        assert.strictEqual($editView.length, 1, "should have edit view menu item");
        assert.strictEqual($editView.text().trim(), "Edit View: List",
            "should have correct menu item text for editing view");
        assert.strictEqual($editView.data('id'), 1, "should have correct view_id");

        debugManager.destroy();
    });

    QUnit.test("Debug: Set defaults with right model", function (assert) {
        assert.expect(2);

        /*  Click on debug > set default,
         *  set some defaults, click on save
         *  model and some other data should be sent to server
         */

        // We'll need a full blown architecture with some data
        var data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: "char", default: "My little Foo Value"},
                },
                records: [{
                    id: 1,
                    foo: "yop",
                }]
            },
            'ir.default': { // We just need this to be defined
                fields: {},
            },
        }

        var form = testUtils.createView({
            View: FormView,
            model: 'partner',
            data: data,
            arch: '<form string="Partners">' +
                    '<field name="foo" />' +
                '</form>',
            res_id: 1,
        });

        // Now the real tested component
        var debugManager = createDebugManager({
            data: data,
            mockRPC: function (route, args) {
                if (route == "/web/dataset/call_kw/ir.default/set") {
                    assert.deepEqual(args.args, ["partner", "foo", "yop", true, true, false],
                        'Model, field, value and booleans for current user/company should have been passed');
                    return $.when();
                }
                return this._super.apply(this, arguments);
            }
        });

        debugManager.appendTo($('#qunit-fixture'));

        // Simulate update debug manager from web client
        var action = {
            views: [{
                fieldsView: {
                    view_id: 1,
                    model: 'partner',
                    type: 'form',
                },
                type: "form",
            }],
            res_model: 'partner',
        };

        // We are all set
        debugManager.update('action', action, form);

        // click on set_defaults dropdown
        debugManager.$('a[data-action="set_defaults"]').click();
        var $modal = $('.modal-content');
        assert.strictEqual($modal.length, 1, 'One modal present');

        $modal.find('select[id=formview_default_fields] option[value=foo]').prop('selected', true);

        // Save
        $modal.find('.modal-footer button').eq(1).click();

        form.destroy();
        debugManager.destroy();
    });
});
});
