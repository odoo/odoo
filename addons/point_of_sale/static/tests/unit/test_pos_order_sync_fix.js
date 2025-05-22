odoo.define('point_of_sale.test_pos_order_sync_fix', function (require) {
"use strict";

const testUtils = require('web.test_utils');
const { createPosEnv } = require('point_of_sale.helpers');

QUnit.module('point_of_sale', {}, function () {

    QUnit.test('Orders should not be removed on backend rejection', async function (assert) {
        assert.expect(4);

        const env = await createPosEnv();
        const pos = env.pos;
        
        // Create a mock order
        const mockOrder = {
            id: 'test-order-1',
            name: 'Order 001',
            pos_reference: 'Order 001',
            export_as_JSON: () => ({
                id: 'test-order-1',
                name: 'Order 001',
                pos_reference: 'Order 001'
            })
        };

        // Add order to db
        pos.db.add_order(mockOrder.export_as_JSON());
        assert.ok(pos.db.get_order('test-order-1'), 'Order should be in database');

        // Mock RPC call that returns empty server_ids (simulating rejection)
        const originalRpc = env.services.rpc;
        env.services.rpc = function(params) {
            if (params.method === 'create_from_ui') {
                // Simulate backend accepting RPC but returning empty results (rejection scenario)
                return Promise.resolve([]);
            }
            return originalRpc.apply(this, arguments);
        };

        try {
            // Attempt to sync the order
            await pos._save_to_server([mockOrder], {});
            
            // Order should still be in database since it wasn't successfully processed
            assert.ok(pos.db.get_order('test-order-1'), 'Order should remain in database after failed processing');
            assert.notOk(pos.syncingOrders.has('test-order-1'), 'Order should not be in syncing set');
            
        } catch (error) {
            // Even if there's an error, order should remain
            assert.ok(pos.db.get_order('test-order-1'), 'Order should remain in database after error');
        }

        // Restore original RPC
        env.services.rpc = originalRpc;
    });

    QUnit.test('Orders should be removed on successful backend processing', async function (assert) {
        assert.expect(3);

        const env = await createPosEnv();
        const pos = env.pos;
        
        // Create a mock order
        const mockOrder = {
            id: 'test-order-2',
            name: 'Order 002',
            pos_reference: 'Order 002',
            export_as_JSON: () => ({
                id: 'test-order-2',
                name: 'Order 002',
                pos_reference: 'Order 002'
            })
        };

        // Add order to db
        pos.db.add_order(mockOrder.export_as_JSON());
        assert.ok(pos.db.get_order('test-order-2'), 'Order should be in database');

        // Mock RPC call that returns successful server_ids
        const originalRpc = env.services.rpc;
        env.services.rpc = function(params) {
            if (params.method === 'create_from_ui') {
                // Simulate successful backend processing
                return Promise.resolve([{
                    id: 123,
                    pos_reference: 'Order 002'
                }]);
            }
            return originalRpc.apply(this, arguments);
        };

        // Attempt to sync the order
        await pos._save_to_server([mockOrder], {});
        
        // Order should be removed from database since it was successfully processed
        assert.notOk(pos.db.get_order('test-order-2'), 'Order should be removed from database after successful processing');
        assert.notOk(pos.syncingOrders.has('test-order-2'), 'Order should not be in syncing set');

        // Restore original RPC
        env.services.rpc = originalRpc;
    });

});

});