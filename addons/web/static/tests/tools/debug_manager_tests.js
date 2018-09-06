odoo.define('web.debugManagerTests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

var createDebugManager = testUtils.createDebugManager;

QUnit.module('DebugManager', {}, function () {

    QUnit.test("list: edit view menu item", function (assert) {
        assert.expect(3);

        var debugManager = createDebugManager();

        debugManager.appendTo($('#qunit-fixture'));

        // Simulate update debug manager from web client
        var action = {
            views: [{
                displayName: "List",
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

    QUnit.test("form: Manage Attachments option", function (assert) {
        assert.expect(3);

        var debugManager = createDebugManager({
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action, {
                      domain: [["res_model", "=", "test.model"],["res_id", "=", 5]],
                      name: "Manage Attachments",
                      res_model: "ir.attachment",
                      type: "ir.actions.act_window",
                      views: [[false, "list"],[false, "form"]],
                    });
                },
            },
        });

        debugManager.appendTo($('#qunit-fixture'));

        // Simulate update debug manager from web client
        var action = {
            views: [{
                displayName: "Form",
                fieldsView: {
                    view_id: 2,
                },
                type: "form",
            }],
            res_model: "test.model",
        };
        var view = {
            viewType: "form",
            getSelectedIds: function () {
                return [5];
            },
        };
        debugManager.update('action', action, view);

        var $attachmentMenu = debugManager.$('a[data-action=get_attachments]');
        assert.strictEqual($attachmentMenu.length, 1, "should have Manage Attachments menu item");
        assert.strictEqual($attachmentMenu.text().trim(), "Manage Attachments",
            "should have correct menu item text");
        $attachmentMenu.click();

        debugManager.destroy();
    });
});
});
