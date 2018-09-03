odoo.define('web.debugManagerTests', function (require) {
"use strict";

var DebugManager = require('web.DebugManager');
var testUtils = require('web.test_utils');

/**
 * Create and return an instance of DebugManager with all rpcs going through a
 * mock method, assuming that the user has access rights, and is an admin.
 *
 * @param {Object} [params={}]
 */
var createDebugManager = function (params) {
    params = params || {};
    _.extend(params, {
        mockRPC: function (route, args) {
            if (args.method === 'check_access_rights') {
                return $.when(true);
            }
            if (args.method === 'xmlid_to_res_id') {
                return $.when(true);
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
            viewName: "List",
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
});
});
