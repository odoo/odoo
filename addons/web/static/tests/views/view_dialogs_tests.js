odoo.define('web.view_dialogs_tests', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var dialogs = require('web.view_dialogs');
var Widget = require('web.Widget');

QUnit.module('Views', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    foo: {string: "Foo", type: 'char'},
                },
                records: [
                    {id: 1, foo: 'blip',},
                ],
            },
        };

    },
}, function () {

    QUnit.module('view_dialogs');

    function createParent(params) {
        var widget = new Widget();

        testUtils.addMockEnvironment(widget, params);
        return widget;
    }

    QUnit.test('formviewdialog buttons in footer are positioned properly', function (assert) {
        assert.expect(2);

        var parent = createParent({
            data: this.data,
            archs: {
                'partner,false,form':
                    '<form string="Partner">' +
                        '<sheet>' +
                            '<group><field name="foo"/></group>' +
                            '<footer><button string="Custom Button" type="object" class="btn-primary"/></footer>' +
                        '</sheet>' +
                    '</form>',
            },
        });

        testUtils.intercept(parent, 'env_updated', function () {
            throw new Error("The environment should not be propagated to the view manager");
        });


        var dialog = new dialogs.FormViewDialog(parent, {
            res_model: 'partner',
            res_id: 1,
        }).open();

        assert.notOk($('div.modal .modal-body button').length,
            "should not have any button in body");
        assert.strictEqual($('div.modal .modal-footer button').length, 1,
            "should have only one button in footer");
        dialog.destroy();
    });

});

});