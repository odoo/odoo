odoo.define('stock.popover_widget_tests', function (require) {
"use strict";

const testUtils = require('web.test_utils');
const FormView = require('web.FormView');
const createView = testUtils.createView;

QUnit.module('widgets', {}, function () {
QUnit.module('ModelFieldSelector', {
    beforeEach: function () {
        this.data = {
            partner: {
                fields: {
                    json_data: {string: " ", type: "char"},
                },
                records: [
                    {id:1, json_data:'{"color": "text-danger", "msg": "var that = self // why not?", "title": "JS Master"}'}
                ]
            }
        };
    },
}, function () {
    QUnit.test("Test creation/usage popover widget form", async function (assert) {
        assert.expect(4);

        const form = await createView({
            View: FormView,
            model: 'partner',
            data: this.data,
            arch: `<form string="Partners">
                    <field name="json_data" widget="popover_widget"/>
                </form>`,
            res_id: 1
        });

        const popoverButton = form.el.querySelector('a.fa.fa-info-circle.text-danger');
        assert.ok(popoverButton, "Should have a popover icon/button in red");

        await testUtils.dom.click(popoverButton);

        const popover = document.querySelector('div.o_popover');
        assert.ok(popover, "Should have a popover container in DOM");
        assert.strictEqual(popover.querySelector('.popover-body').innerText,
            "var that = self // why not?", "The message should be in DOM");
        assert.strictEqual(popover.querySelector('.o_popover_header').innerText,
            "JS Master", "The title should be in DOM");

        form.destroy();
    });
});
});

});
