odoo.define('web.debugManagerTests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var FormView = require('web.FormView');

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
        testUtils.dom.click(debugManager.$('> a')); // open dropdown
        testUtils.dom.click($attachmentMenu);

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
        };

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
            controlPanelFieldsView: {},
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
        testUtils.dom.click(debugManager.$('> a')); // open dropdown
        testUtils.dom.click(debugManager.$('a[data-action="set_defaults"]'));
        var $modal = $('.modal-content');
        assert.strictEqual($modal.length, 1, 'One modal present');

        $modal.find('select[id=formview_default_fields] option[value=foo]').prop('selected', true);

        // Save
        testUtils.dom.click($modal.find('.modal-footer button').eq(1));

        form.destroy();
        debugManager.destroy();
    });
});
});
