/** @odoo-module **/

import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { getFixture } from "@web/../tests/helpers/utils";

QUnit.module('stock_barcode', {}, function () {

QUnit.module('Barcode', {
    beforeEach: function () {
        var self = this;

        this.clientData = {
            action: {
                tag: 'stock_barcode_client_action',
                type: 'ir.actions.client',
                res_model: "stock.picking",
                context: {},
            },
            currentState: {
                actions: {},
                data: {
                    records: {
                        'barcode.nomenclature': [{
                            id: 1,
                            rule_ids: [],
                        }],
                        'stock.location': [],
                        'stock.move.line': [],
                        'stock.picking': [],
                    },
                    nomenclature_id: 1,
                },
                groups: {},
            },
        };
        this.mockRPC = function (route, args) {
            if (route === '/stock_barcode/get_barcode_data') {
                return Promise.resolve(self.clientData.currentState);
            } else if (route === '/stock_barcode/static/img/barcode.svg') {
                return Promise.resolve();
            }
        };
    }
});

QUnit.test('exclamation-triangle when picking is done', async function (assert) {
    assert.expect(1);
    const pickingRecord = {
        id: 2,
        state: 'done',
        move_line_ids: [],
    };
    this.clientData.action.context.active_id = pickingRecord.id;
    this.clientData.currentState.data.records['stock.picking'].push(pickingRecord);
    const target = getFixture();
    const webClient = await createWebClient({
        mockRPC: this.mockRPC,
    });
    await doAction(webClient, this.clientData.action);
    assert.containsOnce(target, '.fa-5x.fa-exclamation-triangle:not(.d-none)', "Should have warning icon");
});

});
