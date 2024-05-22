odoo.define('mail.debugManagerTests', function (require) {
"use strict";

var testUtils = require('web.test_utils');

var createDebugManager = testUtils.createDebugManager;

QUnit.module('Mail DebugManager', {}, function () {

    QUnit.test("Manage Messages", async function (assert) {
        assert.expect(3);

        var debugManager = await createDebugManager({
            intercepts: {
                do_action: function (event) {
                    assert.deepEqual(event.data.action, {
                      context: {
                        default_res_model: "testModel",
                        default_res_id: 5,
                      },
                        res_model: 'mail.message',
                        name: "Manage Messages",
                        views: [[false, 'list'], [false, 'form']],
                        type: 'ir.actions.act_window',
                        domain: [['res_id', '=', 5], ['model', '=', 'testModel']],
                    });
                },
            },
        });

        await debugManager.appendTo($('#qunit-fixture'));

        // Simulate update debug manager from web client
        var action = {
            views: [{
                displayName: "Form",
                fieldsView: {
                    view_id: 1,
                },
                type: "form",
            }],
        };
        var view = {
            viewType: "form",
            getSelectedIds: function () {
                return [5];
            },
            modelName: 'testModel',
        };
        await testUtils.nextTick();
        await debugManager.update('action', action, view);

        var $messageMenu = debugManager.$('a[data-action=getMailMessages]');
        assert.strictEqual($messageMenu.length, 1, "should have Manage Message menu item");
        assert.strictEqual($messageMenu.text().trim(), "Manage Messages",
            "should have correct menu item text");

        await testUtils.dom.click(debugManager.$('> a')); // open dropdown
        await testUtils.dom.click($messageMenu);

        debugManager.destroy();
    });
});
});
