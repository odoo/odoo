import { describe, test, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import {
    getFilledOrder,
    setupPosEnv,
    waitUntilOrdersSynced,
} from "@point_of_sale/../tests/unit/utils";
import { MockServer } from "@web/../tests/_framework/mock_server/mock_server";

const { DateTime } = luxon;

definePosModels();

describe("pos_store.js", () => {
    test("computeTableCount", async () => {
        const store = await setupPosEnv();
        const order1 = store.addNewOrder();
        const table = store.models["restaurant.table"].get(2);
        expect(table.uiState.orderCount).toBe(0);
        order1.table_id = table;
        store.computeTableCount();
        expect(table.uiState.orderCount).toBe(1);
    });

    test("sync dirty order when unsetting table", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = await getFilledOrder(store);
        order.table_id = table;
        expect(store.getPendingOrder().orderToCreate).toHaveLength(1);
        await store.unsetTable();
        await waitUntilOrdersSynced(store);
        expect(store.getPendingOrder().orderToCreate).toHaveLength(0);
        expect(order.isDirty()).toBe(false);
        //Update the order
        order.setInternalNote("Test note");
        expect(order.isDirty()).toBe(true);
        await store.unsetTable();
        await waitUntilOrdersSynced(store);
        expect(order.isDirty()).toBe(false);
        expect(store.getPendingOrder().orderToUpdate).toHaveLength(0);
    });

    describe("class DevicesSynchronisation", () => {
        test("Synchronization for a filled table has arrived", async () => {
            // If a local order is already create on a table when another device send another order
            // for the same table, we merge the orderlines of the local order with the synced order.
            const store = await setupPosEnv();
            const sync = store.deviceSync;
            const table = store.models["restaurant.table"].get(2);
            const filledOrder = await getFilledOrder(store);
            const product1 = filledOrder.lines[0].product_id;
            const product2 = filledOrder.lines[1].product_id;
            filledOrder.table_id = table;

            expect(table.getOrder()).toBe(filledOrder);
            MockServer.env["pos.order"].create({
                config_id: store.config.id,
                session_id: store.session.id,
                table_id: table.id,
                lines: filledOrder.lines.map((line) => [
                    0,
                    0,
                    {
                        product_id: line.product_id.id,
                        price_unit: line.price_unit,
                        qty: 1,
                    },
                ]),
            });

            await sync.collect({
                static_records: {},
                session_id: 1,
                login_number: 0,
                records: {},
            });

            expect(store.models["pos.order"].length).toEqual(1);
            const order = store.models["pos.order"].get(1);
            expect(order.lines).toHaveLength(4);
            expect(table.getOrders()).toHaveLength(1);
            expect(order.lines[0].product_id).toEqual(product1);
            expect(order.lines[1].product_id).toEqual(product2);
            expect(order.lines[2].product_id).toEqual(product1);
            expect(order.lines[3].product_id).toEqual(product2);
            expect(order.lines[0].qty).toEqual(1);
            expect(order.lines[1].qty).toEqual(1);
            expect(order.lines[2].qty).toEqual(3);
            expect(order.lines[3].qty).toEqual(2);
            expect(order.lines[0].id).toBeOfType("number");
            expect(order.lines[1].id).toBeOfType("number");
            expect(order.lines[2].id).toBeOfType("string");
            expect(order.lines[3].id).toBeOfType("string");
            await store.syncAllOrders();
            expect(order.lines[0].id).toBeOfType("number");
            expect(order.lines[1].id).toBeOfType("number");
            expect(order.lines[2].id).toBeOfType("number");
            expect(order.lines[3].id).toBeOfType("number");
        });

        test("Orders must be downloaded by opening a table.", async () => {
            const store = await setupPosEnv();
            const filledOrder = await getFilledOrder(store);
            const table = store.models["restaurant.table"].get(2);
            MockServer.env["pos.order"].create({
                config_id: store.config.id,
                session_id: store.session.id,
                table_id: table.id,
                lines: filledOrder.lines.map((line) => [
                    0,
                    0,
                    {
                        product_id: line.product_id.id,
                        price_unit: line.price_unit,
                        qty: 1,
                    },
                ]),
            });

            // This function is called by setTable in pos_store, but it is not awaited.
            // So we need to await it here to ensure the test runs correctly.
            await store.deviceSync.readDataFromServer();
            expect(table.getOrder().id).toEqual(1);
        });

        test("Orders updated from another device must be synchronized directly.", async () => {
            const store = await setupPosEnv();
            const filledOrder = await getFilledOrder(store);
            const table = store.models["restaurant.table"].get(2);
            filledOrder.table_id = table;
            await store.syncAllOrders();

            expect(filledOrder.id).toBeOfType("number");
            expect(filledOrder.lines).toHaveLength(2);
            expect(filledOrder.table_id).toBe(table);
            MockServer.env["pos.order"].write([filledOrder.id], {
                lines: filledOrder.lines.map((line) => [
                    0,
                    0,
                    {
                        product_id: line.product_id.id,
                        price_unit: line.price_unit,
                        qty: 40,
                    },
                ]),
            });

            await store.deviceSync.readDataFromServer();
            expect(filledOrder.lines).toHaveLength(4);
            expect(filledOrder.lines[2].qty).toEqual(40);
            expect(filledOrder.lines[3].qty).toEqual(40);
            expect(filledOrder.lines[2].id).toBeOfType("number");
            expect(filledOrder.lines[3].id).toBeOfType("number");
        });

        test("Data from other devices overrides local data", async () => {
            const store = await setupPosEnv();
            const filledOrder = await getFilledOrder(store);
            const table = store.models["restaurant.table"].get(2);
            filledOrder.table_id = table;
            filledOrder.internal_note = "Hey give me a discount!";
            await store.syncAllOrders();

            expect(filledOrder.id).toBeOfType("number");
            expect(filledOrder.internal_note).toEqual("Hey give me a discount!");

            filledOrder.internal_note = "Hey give me a discount! But not too much!";
            MockServer.env["pos.order"].write([filledOrder.id], {
                internal_note: "Hey give me a discount!",
            });

            await store.deviceSync.readDataFromServer();
            expect(filledOrder.internal_note).toEqual("Hey give me a discount!");
        });

        test("There should only be one order per table.", async () => {
            const store = await setupPosEnv();
            const table = store.models["restaurant.table"].get(2);
            const date = DateTime.now().toFormat("yyyy-MM-dd HH:mm:ss");
            const filledOrder = await getFilledOrder(store);
            filledOrder.table_id = table;
            await store.syncAllOrders();

            let id = 1;
            let lineId = 1;
            const createOrderForTable = async () => {
                const lines = [
                    {
                        id: `${lineId++}_string`,
                        order_id: 31,
                        product_id: 5,
                        qty: 1,
                        write_date: date,
                    },
                    {
                        id: `${lineId++}_string`,
                        order_id: 31,
                        product_id: 6,
                        qty: 1,
                        write_date: date,
                    },
                ];
                const order = [
                    {
                        id: `${id++}_string`,
                        lines: lines.map((line) => line.id),
                        write_date: date,
                        table_id: table.id,
                        session_id: store.session.id,
                        config_id: store.config.id,
                    },
                ];
                const newData = {
                    "pos.order": order,
                    "pos.order.line": lines,
                };

                await store.deviceSync.processDynamicRecords(newData);
            };

            for (let i = 0; i < 8; i++) {
                await createOrderForTable();
                expect(table.getOrders()).toHaveLength(1);
                expect(table.getOrder().id).toBeOfType("number");
                expect(table.getOrder().lines).toHaveLength(4 + i * 2);
            }

            expect(store.models["pos.order"].length).toEqual(1);
        });
    });
});
