import { describe, test, expect } from "@odoo/hoot";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { MockServer } from "@web/../tests/_framework/mock_server/mock_server";

const { DateTime } = luxon;

definePosModels();

describe("restaurant pos_store.js", () => {
    test("restoreOrdersToOriginalTable", async () => {
        const store = await setupPosEnv();
        const table1 = store.models["restaurant.table"].get(1);
        const table2 = store.models["restaurant.table"].get(2);
        const sourceOrder = store.addNewOrder({ table_id: table1 });
        const product = store.models["product.template"].get(5);
        await store.addLineToOrder(
            {
                product_tmpl_id: product,
                qty: 3,
            },
            sourceOrder
        );
        const line = sourceOrder.lines[0];
        sourceOrder.uiState.unmerge = {
            [line.uuid]: {
                table_id: table2.id,
                quantity: 1,
            },
        };
        const newOrder = await store.restoreOrdersToOriginalTable(sourceOrder, table2);
        expect(newOrder.table_id.id).toBe(table2.id);
        expect(newOrder.lines.length).toBe(1);
    });

    test("fireCourse", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
        const course = store.addCourse();
        store.printCourseTicket = async () => true;
        const result = await store.fireCourse(course);
        expect(course.fired).toBe(true);
        expect(result).toBe(true);
    });

    test("setTable", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const blankOrder = store.addNewOrder();
        expect(blankOrder.table_id).toBe(undefined);
        await store.setTable(table);
        expect(blankOrder.table_id.id).toBe(table.id);
        expect(store.getOrder().id).toBe(blankOrder.id);
    });

    test("computeTableCount", async () => {
        const store = await setupPosEnv();
        const order1 = store.addNewOrder();
        const table = store.models["restaurant.table"].get(2);
        expect(table.uiState.orderCount).toBe(0);
        order1.table_id = table;
        store.computeTableCount();
        expect(table.uiState.orderCount).toBe(1);
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

    test("categoryCount", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        order.lines[0].note = '[{"text":"Test Note","colorIndex":0}]';
        order.lines[1].note = '[{"text":"Test 1","colorIndex":0},{"text":"Test 2","colorIndex":0}]';
        order.general_customer_note = '[{"text":"General Note","colorIndex":0}]';
        const changes = store.categoryCount;
        expect(changes).toEqual([
            { count: 3, name: "Category 1" },
            { count: 2, name: "Category 2" },
            { count: 1, name: "Message" },
        ]);
    });

    test("getDefaultSearchDetails", async () => {
        const store = await setupPosEnv();
        const result = store.getDefaultSearchDetails();
        expect(result).toEqual({
            fieldName: "REFERENCE",
            searchTerm: "",
        });
    });

    test("findTable", async () => {
        const store = await setupPosEnv();
        const table1 = store.models["restaurant.table"].get(2);
        const floor = store.models["restaurant.floor"].get(2);
        store.currentFloor = floor;
        const result = store.findTable("1");
        expect(result.id).toBe(table1.id);
    });

    test("searchOrder", async () => {
        const store = await setupPosEnv();
        const floor = store.models["restaurant.floor"].get(2);
        store.currentFloor = floor;
        const found = store.searchOrder("2");
        expect(found).toBe(true);
        const notFound = store.searchOrder("999");
        expect(notFound).toBe(false);
    });

    test("getTableOrders", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        store.addNewOrder({ table_id: table });
        const orders = store.getTableOrders(table.id);
        expect(orders.length).toBe(1);
    });

    test("getActiveOrdersOnTable", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        store.addNewOrder({ table_id: table });
        store.addNewOrder({ table_id: table });
        const orders = await store.getActiveOrdersOnTable(table);
        expect(orders.length).toBe(2);
    });

    test("prepareOrderTransfer", async () => {
        const store = await setupPosEnv();
        const tableSrc = store.models["restaurant.table"].get(1);
        const tableDst = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: tableSrc });
        store.alert = {
            dismiss: () => {},
        };
        const result = store.prepareOrderTransfer(order, tableDst);
        expect(result).toBe(false);
        expect(order.table_id).toBe(tableDst);
        expect(store.getOrder()).toBe(order);
    });

    test("transferOrder", async () => {
        const store = await setupPosEnv();
        const tableSrc = store.models["restaurant.table"].get(1);
        const tableDst = store.models["restaurant.table"].get(2);
        const sourceOrder = store.addNewOrder({ table_id: tableSrc });
        const product1 = store.models["product.template"].get(5);
        await store.addLineToOrder(
            {
                product_tmpl_id: product1,
                qty: 2,
            },
            sourceOrder
        );
        const order = store.addNewOrder({ table_id: tableDst });
        await store.transferOrder(sourceOrder.uuid, tableDst);
        expect(sourceOrder.lines.length).toBe(0);
        expect(order.lines.length).toBe(1);
        expect(order.table_id.id).toBe(tableDst.id);
    });

    test("mergeOrders merges lines and courses", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const table1 = models["restaurant.table"].get(2);
        const table2 = models["restaurant.table"].get(3);
        const order1 = store.addNewOrder({ table_id: table1 });
        const course1 = store.addCourse();
        const product1 = models["product.template"].get(5);
        const line1 = await store.addLineToOrder({ product_tmpl_id: product1, qty: 1 }, order1);
        line1.course_id = course1;
        course1.line_ids = [line1];
        const order2 = store.addNewOrder({ table_id: table2 });
        const course2 = store.addCourse();
        const product2 = models["product.template"].get(6);
        const line2 = await store.addLineToOrder({ product_tmpl_id: product2, qty: 2 }, order2);
        line2.course_id = course2;
        course2.line_ids = [line2];
        await store.mergeOrders(order1, order2);
        expect(order2.lines.length).toBe(2);
        expect(order1.lines.length).toBe(0);
        expect(order1.table_id).toBe(undefined);
        expect(order2.table_id.id).toBe(table2.id);
        expect(order2.course_ids.length).toBe(1);
        expect(line2.course_id.id).toBe(course2.id);
    });

    test("getCustomerCount", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        store.addNewOrder({ table_id: table }).setCustomerCount(3);
        store.addNewOrder({ table_id: table }).setCustomerCount(6);
        const count = store.getCustomerCount(table.id);
        expect(count).toBe(9);
    });

    test("firstScreen", async () => {
        const store = await setupPosEnv();
        expect(store.firstScreen).toBe("FloorScreen");
    });

    test("setFloatingOrder", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        store.setFloatingOrder(order);
        expect(store.getOrder().id).toBe(order.id);
    });

    describe("addCourse", () => {
        test("creates first course and selects it", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();
            const course = store.addCourse();
            expect(course.order_id).toBe(order);
            expect(order.getSelectedCourse()).toBe(course);
        });

        test("creates second course and assigns existing lines to first", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();
            const product = store.models["product.template"].get(5);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            const course1 = store.addCourse();
            const course2 = order.getSelectedCourse();
            expect(order.course_ids.length).toBe(2);
            expect(course1).not.toBe(course2);
            expect(order.lines[0].course_id).toBe(course1);
        });
    });
});
