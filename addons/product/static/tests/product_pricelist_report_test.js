odoo.define('product.pricelist.report.tests', function (require) {
"use strict";
const GeneratePriceList = require('product.generate_pricelist').GeneratePriceList;
const testUtils = require('web.test_utils');

const { createWebClient, doAction } = require('@web/../tests/webclient/helpers');

let serverData;

QUnit.module('Product Pricelist', {
    beforeEach: function () {
            this.data = {
                'product.product': {
                    fields: {
                        id: {type: 'integer'}
                    },
                    records: [{
                        id: 42,
                        display_name: "Customizable Desk"
                    }]
                },
                'product.pricelist': {
                    fields: {
                        id: {type: 'integer'}
                    },
                    records: [{
                        id: 1,
                        display_name: "Public Pricelist"
                    }, {
                        id: 2,
                        display_name: "Test"
                    }]
                }
            };
            serverData = { models: this.data };
        },
}, function () {
    QUnit.test('Pricelist Client Action', async function (assert) {
        assert.expect(21);

        const self = this;
        let Qty = [1, 5, 10]; // default quantities
        testUtils.mock.patch(GeneratePriceList, {
            _onFieldChanged: function (event) {
                assert.step('field_changed');
                return this._super.apply(this, arguments);
            },
            _onQtyChanged: function (event) {
                assert.deepEqual(event.data.quantities, Qty.sort((a, b) => a - b), "changed quantity should be same.");
                assert.step('qty_changed');
                return this._super.apply(this, arguments);
            },
        });
        const mockRPC = (route, args) => {
            if (route === '/web/dataset/call_kw/report.product.report_pricelist/get_html') {
                return Promise.resolve("");
            }
        };

        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, {
            id: 1,
            name: 'Generate Pricelist',
            tag: 'generate_pricelist',
            type: 'ir.actions.client',
            context: {
                'default_pricelist': 1,
                'active_ids': [42],
                'active_id': 42,
                'active_model': 'product.product'
            }
        });

        // checking default pricelist
        assert.strictEqual($(webClient.el).find('.o_field_many2one input').val(), "Public Pricelist",
            "should have default pricelist");

        // changing pricelist
        await testUtils.fields.many2one.clickOpenDropdown("pricelist_id");
        await testUtils.fields.many2one.clickItem("pricelist_id", "Test");

        // check wherther pricelist value has been updated or not. along with that check default quantities should be there.
        assert.strictEqual($(webClient.el).find('.o_field_many2one input').val(), "Test",
            "After pricelist change, the pricelist_id field should be updated");
        assert.strictEqual($(webClient.el).find('.o_badges > .badge').length, 3,
            "There should be 3 default Quantities");

        // existing quantity can not be added.
        await testUtils.dom.click($(webClient.el).find('.o_add_qty'));
        let notificationElement = document.body.querySelector('.o_notification_manager .o_notification.bg-info');
        assert.strictEqual(notificationElement.querySelector('.o_notification_content').textContent,
            "Quantity already present (1).", "Existing Quantity can not be added");

        // adding few more quantities to check.
        $(webClient.el).find('.o_product_qty').val(2);
        Qty.push(2);
        await testUtils.dom.click($(webClient.el).find('.o_add_qty'));
        $(webClient.el).find('.o_product_qty').val(3);
        Qty.push(3);
        await testUtils.dom.click($(webClient.el).find('.o_add_qty'));

        // should not be added more then 5 quantities.
        $(webClient.el).find('.o_product_qty').val(4);
        await testUtils.dom.click($(webClient.el).find('.o_add_qty'));

        notificationElement = document.body.querySelector('.o_notification_manager .o_notification.bg-warning');
        assert.strictEqual(notificationElement.querySelector('.o_notification_content').textContent,
            "At most 5 quantities can be displayed simultaneously. Remove a selected quantity to add others.",
            "Can not add more then 5 quantities");

        // removing all the quantities should work
        Qty.pop(10);
        await testUtils.dom.click($(webClient.el).find('.o_badges .badge:contains("10") .o_remove_qty'));
        Qty.pop(5);
        await testUtils.dom.click($(webClient.el).find('.o_badges .badge:contains("5") .o_remove_qty'));
        Qty.pop(3);
        await testUtils.dom.click($(webClient.el).find('.o_badges .badge:contains("3") .o_remove_qty'));
        Qty.pop(2);
        await testUtils.dom.click($(webClient.el).find('.o_badges .badge:contains("2") .o_remove_qty'));
        Qty.pop(1);
        await testUtils.dom.click($(webClient.el).find('.o_badges .badge:contains("1") .o_remove_qty'));

        assert.verifySteps([
            'field_changed',
            'qty_changed',
            'qty_changed',
            'qty_changed',
            'qty_changed',
            'qty_changed',
            'qty_changed',
            'qty_changed'
        ]);

        testUtils.mock.unpatch(GeneratePriceList);
    });
}

);
});
