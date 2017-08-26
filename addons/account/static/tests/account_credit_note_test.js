odoo.define('account.credit_note_button', function (require) {
"use strict";

var testUtils = require('web.test_utils');
var view_registry = require('web.view_registry');

var createView = testUtils.createView;

QUnit.module('account', {
    beforeEach: function () {
        this.data = {
            'account.invoice': {
                fields: {
                    foo: {string: 'Foo', type: 'char'},
                    bar: {string: 'Bar', type: 'boolean'},
                },
                records: [
                    {id: 1, foo: 'yop', bar: true},
                    {id: 2, foo: 'blip', bar: true},
                    {id: 3, foo: 'gnap', bar: true},
                ]
            },
        };
    }
}, function () {
    QUnit.module('Account Credit Note');

    QUnit.test('Check buttons rendered properly in list view', function (assert) {
        assert.expect(3);

        var list = createView({
            View: view_registry.get('credit_note_list_view'),
            model: 'account.invoice',
            data: this.data,
            arch: '<tree><field name="foo"/><field name="bar"/></tree>',
            intercepts: {
                do_action: function (event) {
                    assert.strictEqual(event.data.action, 'account.account_invoice_action_in_refund_new',
                        'should open the form view action');
                },
            },
        });

        assert.strictEqual(list.$buttons.find('.o_list_button_add').length, 1, 'should have a create button');
        assert.strictEqual(list.$buttons.find('.o_button_credit_note').length, 1, 'should have a New Credit Note button');
        list.$buttons.find('.o_button_credit_note').click();
        list.destroy();
    });

    QUnit.test('Check buttons rendered properly in form view', function (assert) {
        assert.expect(3);

        var form = createView({
            View: view_registry.get('credit_note_form_view'),
            model: 'account.invoice',
            data: this.data,
            arch: '<form>' +
                    '<sheet>' +
                        '<group>' +
                            '<field name="foo"/>' +
                            '<field name="bar"/>' +
                        '</group>' +
                    '</sheet>' +
                  '</form>',
            intercepts: {
                do_action: function (event) {
                    assert.strictEqual(event.data.action, 'account.account_invoice_action_in_refund_new',
                        'should open the form view action');
                },
            },
        });

        assert.strictEqual(form.$buttons.find('.o_form_button_create').length, 1, 'should have a create button');
        assert.strictEqual(form.$buttons.find('.o_button_credit_note').length, 1, 'should have a New Credit Note button');
        form.$buttons.find('.o_button_credit_note').click();
        form.destroy();
    });
});

});
