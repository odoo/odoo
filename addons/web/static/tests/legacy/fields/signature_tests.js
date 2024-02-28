odoo.define('web.signature_field_tests', function (require) {
"use strict";

var FormView = require('web.FormView');
var testUtils = require('web.test_utils');

var createView = testUtils.createView;

QUnit.module('fields', {}, function () {

QUnit.module('signature legacy', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    display_name: {string: "Name", type: "char" },
                    product_id: {string: "Product Name", type: "many2one", relation: 'product'},
                    sign: {string: "Signature", type: "binary"},
                },
                records: [{
                    id: 1,
                    display_name: "Pop's Chock'lit",
                    product_id: 7,
                }],
                onchanges: {},
            },
            product: {
                fields: {
                    name: {string: "Product Name", type: "char"}
                },
                records: [{
                    id: 7,
                    display_name: "Veggie Burger",
                }]
            },
        };
    }
}, function () {
    QUnit.test('Set simple field in "full_name" node option', async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<field name="display_name"/>' +
                    '<field name="sign" widget="signature" options="{\'full_name\': \'display_name\'}" />' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/sign/get_fonts/') {
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        });

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, 'div[name=sign] div.o_signature svg',
            "should have a valid signature widget");
        // Click on the widget to open signature modal
        await testUtils.dom.click(form.$('div[name=sign] div.o_signature'));
        assert.strictEqual($('.modal .modal-body a.o_web_sign_auto_button').length, 1,
            'should open a modal with "Auto" button');
        assert.strictEqual($('.modal .modal-body .o_web_sign_name_input').val(), "Pop's Chock'lit",
            'Correct Value should be set in the input for auto drawing the signature');

        form.destroy();
    });

    QUnit.test('Set m2o field in "full_name" node option', async function (assert) {
        assert.expect(3);

        var form = await createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<field name="product_id"/>' +
                    '<field name="sign" widget="signature" options="{\'full_name\': \'product_id\'}" />' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/sign/get_fonts/') {
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        });

        await testUtils.form.clickEdit(form);

        assert.containsOnce(form, 'div[name=sign] div.o_signature svg',
            "should have a valid signature widget");
        // Click on the widget to open signature modal
        await testUtils.dom.click(form.$('div[name=sign] div.o_signature'));
        assert.strictEqual($('.modal .modal-body a.o_web_sign_auto_button').length, 1,
            'should open a modal with "Auto" button');
        assert.strictEqual($('.modal .modal-body .o_web_sign_name_input').val(), "Veggie Burger",
            'Correct Value should be set in the input for auto drawing the signature');

        form.destroy();
    });

    QUnit.module('Signature Widget');

    QUnit.test('Signature widget renders a Sign button', async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<header>' +
                        '<widget name="signature" string="Sign"/>' +
                    '</header>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/sign/get_fonts/') {
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        });

        assert.containsOnce(form, 'button.o_sign_button.o_widget',
            "Should have a signature widget button");
        assert.strictEqual($('.modal-dialog').length, 0,
            "Should not have any modal");
        // Clicks on the sign button to open the sign modal.
        await testUtils.dom.click(form.$('span.o_sign_label'));
        assert.strictEqual($('.modal-dialog').length, 1,
            "Should have one modal opened");

        form.destroy();
    });

    QUnit.test('Signature widget: full_name option', async function (assert) {
        assert.expect(2);

        const form = await createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<header>' +
                        '<widget name="signature" string="Sign" full_name="display_name"/>' +
                    '</header>' +
                    '<field name="display_name"/>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/sign/get_fonts/') {
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        });

        // Clicks on the sign button to open the sign modal.
        await testUtils.dom.click(form.$('span.o_sign_label'));
        assert.strictEqual($('.modal .modal-body a.o_web_sign_auto_button').length, 1,
            "Should open a modal with \"Auto\" button");
        assert.strictEqual($('.modal .modal-body .o_web_sign_name_input').val(), "Pop's Chock'lit",
            "Correct Value should be set in the input for auto drawing the signature");

        form.destroy();
    });

    QUnit.test('Signature widget: highlight option', async function (assert) {
        assert.expect(3);

        const form = await createView({
            View: FormView,
            model: 'partner',
            res_id: 1,
            data: this.data,
            arch: '<form>' +
                    '<header>' +
                        '<widget name="signature" string="Sign" highlight="1"/>' +
                    '</header>' +
                '</form>',
            mockRPC: function (route, args) {
                if (route === '/web/sign/get_fonts/') {
                    return Promise.resolve();
                }
                return this._super(route, args);
            },
        });

        assert.hasClass(form.$('button.o_sign_button.o_widget'), 'btn-primary',
            "The button must have the 'btn-primary' class as \"highlight=1\"");
        // Clicks on the sign button to open the sign modal.
        await testUtils.dom.click(form.$('span.o_sign_label'));
        assert.isNotVisible($('.modal .modal-body a.o_web_sign_auto_button'),
            "\"Auto\" button must be invisible");
        assert.strictEqual($('.modal .modal-body .o_web_sign_name_input').val(), '',
            "No value should be set in the input for auto drawing the signature");

        form.destroy();
    });
});
});
});
