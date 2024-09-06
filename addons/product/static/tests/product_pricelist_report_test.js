/** @odoo-module **/

import {
    click,
    editSelect,
    editInput,
    findElement,
    getFixture,
    patchWithCleanup
} from "@web/../tests/helpers/utils";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { ProductPricelistReport } from "@product/js/pricelist_report/product_pricelist_report";


let serverData;

QUnit.module('Product Pricelist Report', {
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
                        name: "Public Pricelist",
                        display_name: "Public Pricelist"
                    }, {
                        id: 2,
                        name: "Test",
                        display_name: "Test"
                    }]
                }
            };
            serverData = { models: this.data };
        },
}, function () {
    QUnit.test('Pricelist Client Action', async function (assert) {
        assert.expect(18);

        let Qty = [1, 5, 10]; // default quantities
        patchWithCleanup(ProductPricelistReport.prototype, {
                onSelectPricelist(event) {
                    assert.step('pricelist_changed');
                    super.onSelectPricelist(...arguments)
                },
                onClickAddQty(event) {
                    assert.deepEqual(this.quantities, Qty.sort((a, b) => a - b), "changed quantity should be same.");
                    assert.step('qty_added');
                    super.onClickAddQty(...arguments);
                },
            });

        const mockRPC = (route, args) => {
            if (route === '/web/dataset/call_kw/report.product.report_pricelist/get_html') {
                return Promise.resolve("");
            }
        };

        const target = getFixture();
        const webClient = await createWebClient({ serverData, mockRPC });
        await doAction(webClient, {
            id: 1,
            name: 'Generate Pricelist Report',
            tag: 'generate_pricelist_report',
            type: 'ir.actions.client',
            context: {
                'active_ids': [42],
                'active_model': 'product.product',
            }
        });
        const selectElement = findElement(target, 'select#pricelists');
        const badgesElement = findElement(target, '.o_badges_list');
        const inputElement = findElement(target, '.add-quantity-input');
        const addQtyButton = findElement(target, '.o_add_qty');

        // checking default pricelist
       assert.strictEqual(selectElement.children[0].text, "Public Pricelist", "should have default pricelist");

        // changing pricelist
        await editSelect(selectElement, '', 2);

        // check wherther pricelist value has been updated or not
        assert.strictEqual(selectElement.children[0].text, "Test",
            "After pricelist change, the pricelist_id field should be updated");

        // check default quantities should be there
        assert.strictEqual(badgesElement.children.length, 3, "There should be 3 default quantities");

        // existing quantity can not be added.
        await click(addQtyButton);
        let notificationElement = document.body.querySelector('.o_notification_manager .o_notification');
        let notificationElementBar = document.body.querySelector('.o_notification_manager .o_notification .o_notification_bar');
        assert.strictEqual(notificationElement.querySelector('.o_notification_content').textContent,
            "Quantity already present (1).", "Existing Quantity can not be added");
        assert.hasClass(notificationElementBar, "bg-info");

        // adding few more quantities to check.
        await editInput(inputElement, '', 2);
        await click(addQtyButton);
        Qty.push(2);

        await editInput(inputElement, '', 3);
        await click(addQtyButton);
        Qty.push(3);

        // check quantities were added
        assert.strictEqual(badgesElement.children.length, 5, "There should be 5 different quantities");

        // no more than 5 quantities can be used at a time
        await editInput(inputElement, '', 4);
        await click(addQtyButton);
        notificationElement = document.body.querySelector('.o_notification_manager .o_notification:nth-child(2)');
        notificationElementBar = document.body.querySelector('.o_notification_manager .o_notification:nth-child(2) .o_notification_bar');
        assert.strictEqual(notificationElement.querySelector('.o_notification_content').textContent,
            "At most 5 quantities can be displayed simultaneously. Remove a selected quantity to add others.",
            "Can not add more then 5 quantities");
        assert.hasClass(notificationElementBar, "bg-warning");

        assert.verifySteps([
            'pricelist_changed',
            'qty_added',
            'qty_added',
            'qty_added',
            'qty_added',
        ]);
    });
});
