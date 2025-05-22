odoo.define('point_of_sale.test_pos_order_removal_fix', function (require) {
"use strict";

const testUtils = require('web.test_utils');
const { createPosEnv } = require('point_of_sale.helpers');

QUnit.module('point_of_sale', {}, function () {

    QUnit.test('Orders should remain in localStorage when not in server response', async function (assert) {
        assert.expect(3);

        const env = await createPosEnv();
        const pos = env.pos;
        
        // Create mock orders
        const mockOrder1 = {
            id: 'test-order-1',
            name: 'Order 001',
            pos_reference: 'Order 001',
            export_as_JSON: () => ({ id: 'test-order-1', name: 'Order 001', pos_reference: 'Order 001' })
        };
        
        const mockOrder2 = {
            id: 'test-order-2', 
            name: 'Order 002',
            pos_reference: 'Order 002',
            export_as_JSON: () => ({ id: 'test-order-2', name: 'Order 002', pos_reference: 'Order 002' })
        };

        // Add orders to db
        pos.db.add_order(mockOrder1.export_as_JSON());
        pos.db.add_order(mockOrder2.export_as_JSON());
        assert.equal(pos.db.get_orders().length, 2, 'Both orders should be in database');

        // Mock RPC call that only returns success for one order (simulating partial processing)
        const originalRpc = env.services.rpc;
        env.services.rpc = function(params) {
            if (params.method === 'create_from_ui') {
                // Simulate backend only processing one order successfully
                return Promise.resolve([{
                    id: 123,
                    pos_reference: 'Order 001'  // Only Order 001 was processed
                }]);
            }
            return originalRpc.apply(this, arguments);
        };

        // Attempt to sync both orders
        await pos._save_to_server([mockOrder1, mockOrder2], {});
        
        // Only the processed order should be removed from database
        const remainingOrders = pos.db.get_orders();
        assert.equal(remainingOrders.length, 1, 'One order should remain in database');
        assert.equal(remainingOrders[0].name, 'Order 002', 'Unprocessed order should remain');

        // Restore original RPC
        env.services.rpc = originalRpc;
    });

    QUnit.test('All orders removed when all are in server response', async function (assert) {
        assert.expect(2);

        const env = await createPosEnv();
        const pos = env.pos;
        
        // Create mock orders
        const mockOrder1 = {
            id: 'test-order-3',
            name: 'Order 003', 
            pos_reference: 'Order 003',
            export_as_JSON: () => ({ id: 'test-order-3', name: 'Order 003', pos_reference: 'Order 003' })
        };
        
        const mockOrder2 = {
            id: 'test-order-4',
            name: 'Order 004',
            pos_reference: 'Order 004', 
            export_as_JSON: () => ({ id: 'test-order-4', name: 'Order 004', pos_reference: 'Order 004' })
        };

        // Add orders to db
        pos.db.add_order(mockOrder1.export_as_JSON());
        pos.db.add_order(mockOrder2.export_as_JSON());
        assert.equal(pos.db.get_orders().length, 2, 'Both orders should be in database');

        // Mock RPC call that returns success for both orders
        const originalRpc = env.services.rpc;
        env.services.rpc = function(params) {
            if (params.method === 'create_from_ui') {
                // Simulate backend processing both orders successfully
                return Promise.resolve([
                    { id: 123, pos_reference: 'Order 003' },
                    { id: 124, pos_reference: 'Order 004' }
                ]);
            }
            return originalRpc.apply(this, arguments);
        };

        // Attempt to sync both orders
        await pos._save_to_server([mockOrder1, mockOrder2], {});
        
        // Both orders should be removed since both were processed
        assert.equal(pos.db.get_orders().length, 0, 'No orders should remain in database');

        // Restore original RPC
        env.services.rpc = originalRpc;
    });

    QUnit.test('All orders remain when server returns empty response', async function (assert) {
        assert.expect(2);

        const env = await createPosEnv();
        const pos = env.pos;
        
        // Create mock order
        const mockOrder = {
            id: 'test-order-5',
            name: 'Order 005',
            pos_reference: 'Order 005',
            export_as_JSON: () => ({ id: 'test-order-5', name: 'Order 005', pos_reference: 'Order 005' })
        };

        // Add order to db
        pos.db.add_order(mockOrder.export_as_JSON());
        assert.equal(pos.db.get_orders().length, 1, 'Order should be in database');

        // Mock RPC call that returns empty response (no orders processed)
        const originalRpc = env.services.rpc;
        env.services.rpc = function(params) {
            if (params.method === 'create_from_ui') {
                // Simulate backend not processing any orders
                return Promise.resolve([]);
            }
            return originalRpc.apply(this, arguments);
        };

        // Attempt to sync order
        await pos._save_to_server([mockOrder], {});
        
        // Order should remain since it wasn't processed
        assert.equal(pos.db.get_orders().length, 1, 'Order should remain in database');

        // Restore original RPC
        env.services.rpc = originalRpc;
    });

});

});