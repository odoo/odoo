import { describe, expect, test, tick } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import OrderPaymentValidation from "@point_of_sale/app/utils/order_payment_validation";
import {
    getFilledOrder,
    setupPosEnv,
    waitUntilOrdersSynced,
} from "@point_of_sale/../tests/unit/utils";
import { MockServer } from "@web/../tests/web_test_helpers";

const { DateTime } = luxon;

definePosModels();

describe("restaurant pos_store.js", () => {
    test("fireCourse", async () => {
        const store = await setupPosEnv();
        store.addNewOrder();
        const course = store.addCourse();
        store.printCourseTicket = async () => true;
        const result = await store.fireCourse(course);
        expect(course.fired).toBe(true);
        expect(result).toBe(true);
    });

    test("printCourseTicket builds note update payload", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const course = store.addCourse();
        order.lines[0].course_id = course;
        course.line_ids = [order.lines[0]];

        let captured = null;
        store.ticketPrinter.printOrderChanges = async ({ opts }) => {
            captured = opts.orderChange;
            return true;
        };

        await store.printCourseTicket(course);

        expect(captured.noteUpdateTitle).toBe("Course 1 fired");
        expect(captured.printNoteUpdateData).toBe(false);
        expect(captured.noteUpdate).toHaveLength(1);
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

    test("getChanges", async () => {
        const store = await setupPosEnv();
        const product = store.models["product.product"].get(5);
        product.display_name = "001 TEST";
        const order = await getFilledOrder(store);
        const result = order.getChanges();
        const [line] = Object.values(result.addedQuantity);
        expect(line.basic_name).toBe("TEST");
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
                device_identifier: 0,
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

        test("paid state from server is synchronized", async () => {
            const store = await setupPosEnv();
            const table = store.models["restaurant.table"].get(2);

            MockServer.env["pos.order"].create({
                config_id: store.config.id,
                session_id: store.session.id,
                table_id: table.id,
                lines: [
                    [
                        0,
                        0,
                        {
                            product_id: 5,
                            qty: 50,
                            price_unit: 2.2,
                        },
                    ],
                    [
                        0,
                        0,
                        {
                            product_id: 6,
                            qty: 30,
                            price_unit: 2.2,
                        },
                    ],
                ],
                state: "draft",
            });

            await store.deviceSync.readDataFromServer();
            const syncedOrder = table.getOrder();
            expect(syncedOrder.state).toBe("draft");
            expect(syncedOrder.lines).toHaveLength(2);

            MockServer.env["pos.order"].write([syncedOrder.id], {
                state: "paid",
            });

            await store.deviceSync.readDataFromServer();
            const latestSyncedOrder = store.models["pos.order"].getFirst();
            expect(latestSyncedOrder.state).toBe("paid");
            expect(latestSyncedOrder.lines[0].qty).toBe(50);
            expect(latestSyncedOrder.lines[1].qty).toBe(30);
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
                const orderId = `${id++}_string`;
                const lines = [
                    {
                        id: `${lineId++}_string`,
                        order_id: orderId,
                        product_id: 5,
                        qty: 1,
                        write_date: date,
                    },
                    {
                        id: `${lineId++}_string`,
                        order_id: orderId,
                        product_id: 6,
                        qty: 1,
                        write_date: date,
                    },
                ];
                const order = [
                    {
                        id: orderId,
                        lines: lines.map((line) => line.id),
                        write_date: date,
                        table_id: table.id,
                        pos_reference: "000-0-000000",
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

    describe("categoryCount", () => {
        test("Normal flow", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);
            order.lines[0].note = '[{"text":"Test Note","colorIndex":0}]';
            order.lines[1].note =
                '[{"text":"Test 1","colorIndex":0},{"text":"Test 2","colorIndex":0}]';
            order.general_customer_note = '[{"text":"General Note","colorIndex":0}]';
            const changes = store.getOrder().preparationChanges.categoryCount;
            expect(changes).toEqual([
                { count: 3, name: "Category 1" },
                { count: 2, name: "Category 2" },
                { count: 1, name: "Message" },
            ]);
        });

        test("multi-category product counts only first category", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();
            const multiCategoryProduct = store.models["product.template"].get(19);
            await store.addLineToOrder({ product_tmpl_id: multiCategoryProduct, qty: 1 }, order);

            const changes = order.preparationChanges.categoryCount;

            expect(changes.some((entry) => entry.name === "Category 1")).toBe(true);
            expect(changes.some((entry) => entry.name === "Category 2")).toBe(false);
        });
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
        const found = store.searchOrder("1");
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
        const date = DateTime.now();
        const tableSrc = store.models["restaurant.table"].get(1);
        const tableDst = store.models["restaurant.table"].get(2);
        const sourceOrder = store.addNewOrder({
            table_id: tableSrc,
            write_date: date,
            create_date: date,
        });
        const product1 = store.models["product.template"].get(5);
        await store.addLineToOrder(
            {
                product_tmpl_id: product1,
                qty: 2,
                write_date: date,
                create_date: date,
            },
            sourceOrder
        );
        const order = store.addNewOrder({
            table_id: tableDst,
            write_date: date,
            create_date: date,
        });
        await store.transferOrder(sourceOrder.uuid, tableDst);
        expect(sourceOrder.lines.length).toBe(0);
        expect(order.lines.length).toBe(1);
        expect(order.table_id.id).toBe(tableDst.id);
    });

    test("transferOrder from floating order to filled table merges lines", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const sourceOrder = store.addNewOrder({ floating_order_name: "Float A" });
        const destinationOrder = store.addNewOrder({ table_id: table });
        const product1 = store.models["product.template"].get(5);
        const product2 = store.models["product.template"].get(6);

        await store.addLineToOrder({ product_tmpl_id: product1, qty: 2 }, sourceOrder);
        await store.addLineToOrder({ product_tmpl_id: product2, qty: 1 }, destinationOrder);

        await store.transferOrder(sourceOrder.uuid, null, destinationOrder);

        expect(sourceOrder.lines.length).toBe(0);
        expect(store.models["pos.order"].getBy("uuid", sourceOrder.uuid)).toBeEmpty();
        expect(destinationOrder.lines.length).toBe(2);
    });

    test("floating order transfers into another floating order", async () => {
        const store = await setupPosEnv();
        const sourceOrder = store.addNewOrder({ floating_order_name: "Cola" });
        const destinationOrder = store.addNewOrder({ floating_order_name: "Water" });
        const cola = store.models["product.template"].get(5);
        const water = store.models["product.template"].get(6);
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 3 }, sourceOrder);
        await store.addLineToOrder({ product_tmpl_id: water, qty: 3 }, destinationOrder);

        await store.transferOrder(sourceOrder.uuid, null, destinationOrder);

        expect(store.models["pos.order"].getBy("uuid", sourceOrder.uuid)).toBeEmpty();
        expect(destinationOrder.lines.length).toBe(2);
        expect(destinationOrder.lines[0].qty).toBe(3);
        expect(destinationOrder.lines[1].qty).toBe(3);
    });

    test("preSyncAllOrders assigns floating order name to direct sale", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        await store.preSyncAllOrders([order]);
        expect(Boolean(order.floating_order_name)).toBe(true);
    });

    test("sync updates quantity, partner, note, line note and pricelist", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const table = store.models["restaurant.table"].get(2);
        const partner = store.models["res.partner"].get(3);
        const pricelist = store.models["product.pricelist"].get(2);
        order.table_id = table;

        await store.syncAllOrders();
        const line = order.lines[0];

        line.setQuantity(2);
        expect(order.isDirty()).toBe(true);

        MockServer.env["pos.order"].write([order.id], {
            partner_id: partner.id,
            internal_note: '[{"text":"Hello world","colorIndex":0}]',
            pricelist_id: pricelist.id,
        });
        MockServer.env["pos.order.line"].write([line.id], {
            qty: 3,
            note: '[{"text":"Demo note","colorIndex":0}]',
        });

        await store.deviceSync.readDataFromServer();

        expect(order.lines[0].qty).toBe(3);
        expect(order.partner_id.id).toBe(partner.id);
        expect(order.internal_note).toBe('[{"text":"Hello world","colorIndex":0}]');
        expect(order.lines[0].note).toBe('[{"text":"Demo note","colorIndex":0}]');
        expect(order.pricelist_id.id).toBe(pricelist.id);
        expect(order.isDirty()).toBe(false);
    });

    test("cancel order keeps lines on first reject and removes on confirm", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const cola = store.models["product.template"].get(5);
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 1 }, order);

        let attempts = 0;
        store.beforeDeleteOrder = async () => {
            attempts++;
            return attempts > 1;
        };

        const firstTry = await store.onDeleteOrder(order);
        expect(firstTry).toBe(false);
        expect(store.models["pos.order"].getBy("uuid", order.uuid)).not.toBeEmpty();

        const secondTry = await store.onDeleteOrder(order);
        expect(secondTry).toBe(true);
        expect(store.models["pos.order"].getBy("uuid", order.uuid)).toBeEmpty();
        expect(table.getOrders().length).toBe(0);
    });

    test("order has no pending line changes after sending", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const cola = store.models["product.template"].get(5);
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 1 }, order);

        await store.sendOrderInPreparationUpdateLastChange(order);
        const changes = order.preparationChanges;

        expect(changes.quantity).toBe(0);
    });

    test("firing first course highlights next", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const cola = store.models["product.template"].get(5);
        const water = store.models["product.template"].get(6);
        const juice = store.models["product.template"].get(11);
        const date = DateTime.now();
        order.write_date = date;
        order.create_date = date;

        const course1 = store.addCourse();
        const line1 = await store.addLineToOrder(
            {
                product_tmpl_id: cola,
                qty: 3,
                write_date: date,
                create_date: date,
            },
            order
        );
        line1.course_id = course1;
        course1.line_ids = [line1];
        const course2 = store.addCourse();
        const line2 = await store.addLineToOrder(
            {
                product_tmpl_id: water,
                qty: 3,
                write_date: date,
                create_date: date,
            },
            order
        );
        line2.course_id = course2;
        course2.line_ids = [line2];
        const course3 = store.addCourse();
        const line3 = await store.addLineToOrder(
            {
                product_tmpl_id: juice,
                qty: 1,
                write_date: date,
                create_date: date,
            },
            order
        );
        line3.course_id = course3;
        course3.line_ids = [line3];
        store.printCourseTicket = async () => true;

        await store.fireCourse(course1);
        expect(course1.fired).toBe(true);
        order?.ensureCourseSelection();
        expect(order.getSelectedCourse().uuid).toBe(course2.uuid);
        await store.fireCourse(course2);
        expect(course2.fired).toBe(true);
        order?.ensureCourseSelection();
        expect(order.getSelectedCourse().uuid).toBe(course3.uuid);
    });

    test("combo synchronisation keeps combo links after synced update", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const comboTemplate = store.models["product.template"].get(7);
        const comboItem1 = store.models["product.combo.item"].get(1);
        const comboItem2 = store.models["product.combo.item"].get(3);

        const comboParent = await store.addLineToOrder(
            {
                product_tmpl_id: comboTemplate,
                payload: [
                    [
                        {
                            combo_item_id: comboItem1,
                            qty: 1,
                        },
                        {
                            combo_item_id: comboItem2,
                            qty: 1,
                        },
                    ],
                    [],
                ],
                configure: true,
            },
            order
        );

        await store.syncAllOrders();
        order.setPartner(store.models["res.partner"].get(3));
        await store.syncAllOrders({ orders: [order] });

        expect(comboParent.combo_line_ids.length).toBe(2);
        expect(comboParent.combo_line_ids[0].combo_parent_id).toBe(comboParent);
        expect(comboParent.combo_line_ids[1].combo_parent_id).toBe(comboParent);
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
        const table1InternalNote = '[{"text":"Table 1 kitchen note","colorIndex":0}]';
        const table2InternalNote = '[{"text":"Table 2 kitchen note","colorIndex":0}]';
        order1.pushLastPrints({
            addedQuantity: [{ product_id: 99, quantity: 1 }],
            removedQuantity: [],
            noteUpdate: [],
            noteChange: false,
        });
        order1.pushLastPrints({
            addedQuantity: [],
            removedQuantity: [{ product_id: product1.id, quantity: 1 }],
            noteUpdate: [],
            noteChange: false,
            internal_note: table1InternalNote,
        });
        order2.pushLastPrints({
            addedQuantity: [{ product_id: 100, quantity: 1 }],
            removedQuantity: [],
            noteUpdate: [],
            noteChange: false,
        });
        order2.pushLastPrints({
            addedQuantity: [{ product_id: product2.id, quantity: 2 }],
            removedQuantity: [],
            noteUpdate: [],
            noteChange: false,
            internal_note: table2InternalNote,
        });
        await store.mergeOrders(order1, order2);
        expect(order2.lines.length).toBe(2);
        expect(order1.lines.length).toBe(0);
        expect(order1.table_id).toBe(undefined);
        expect(order2.table_id.id).toBe(table2.id);
        expect(order2.course_ids.length).toBe(1);
        expect(line2.course_id.id).toBe(course2.id);
        const lastPrint = order2.lastPrints.at(-1);
        expect(lastPrint).not.toBe(undefined);
        expect(lastPrint.addedQuantity.length).toBe(1);
        expect(lastPrint.addedQuantity[0].product_id).toBe(product2.id);
        expect(lastPrint.removedQuantity.length).toBe(1);
        expect(lastPrint.removedQuantity[0].product_id).toBe(product1.id);
        expect(lastPrint.internal_note).toBe(table2InternalNote);
    });

    test("mergeOrders sums guest counts", async () => {
        const store = await setupPosEnv();
        const models = store.models;
        const table1 = models["restaurant.table"].get(2);
        const table2 = models["restaurant.table"].get(3);
        const order1 = store.addNewOrder({ table_id: table1 });
        order1.setCustomerCount(3);
        const order2 = store.addNewOrder({ table_id: table2 });
        order2.setCustomerCount(5);
        await store.mergeOrders(order1, order2);
        expect(order2.getCustomerCount()).toBe(8);
    });

    test("mergeOrders keeps kitchen sent quantities when merging identical products", async () => {
        const store = await setupPosEnv();
        const table6 = store.models["restaurant.table"].get(2);
        const table7 = store.models["restaurant.table"].get(3);
        const product = store.models["product.template"].get(5);
        const destOrder = store.addNewOrder({ table_id: table6 });
        await store.addLineToOrder({ product_tmpl_id: product, qty: 2 }, destOrder);
        destOrder.updateLastOrderChange();
        const sourceOrder = store.addNewOrder({ table_id: table7 });
        await store.addLineToOrder({ product_tmpl_id: product, qty: 3 }, sourceOrder);
        sourceOrder.updateLastOrderChange();
        await store.mergeOrders(sourceOrder, destOrder);
        expect(destOrder.lines.length).toBe(1);
        expect(destOrder.lines[0].qty).toBe(5);
        expect(destOrder.lines[0].prepQty).toBe(5);
        const changes = destOrder.getChanges();
        expect(changes.addedQuantity.length).toBe(0);
        expect(changes.removedQuantity.length).toBe(0);
    });

    test("getCustomerCount", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        store.addNewOrder({ table_id: table }).setCustomerCount(3);
        store.addNewOrder({ table_id: table }).setCustomerCount(6);
        const count = store.getCustomerCount(table.id);
        expect(count).toBe(9);
    });

    test("firstPage", async () => {
        const store = await setupPosEnv();
        expect(store.firstPage.page).toBe("LoginScreen");
    });

    test("defaultPage uses ProductScreen when default_screen is register", async () => {
        const store = await setupPosEnv();
        store.config.default_screen = "register";
        const order = store.addNewOrder();
        store.setOrder(order);

        expect(store.defaultPage.page).toBe("ProductScreen");
        expect(store.defaultPage.params.orderUuid).toBe(order.uuid);
    });

    test("showDefault navigates to ProductScreen with selected order in register mode", async () => {
        const store = await setupPosEnv();
        store.config.default_screen = "register";
        const order = store.addNewOrder();
        store.setOrder(order);
        let destination = null;

        store.navigate = (page, params) => {
            destination = { page, params };
        };

        store.showDefault();

        expect(destination.page).toBe("ProductScreen");
        expect(destination.params.orderUuid).toBe(order.uuid);
    });

    test("showDefault", async () => {
        const store = await setupPosEnv();
        store.config.default_screen = "register";
        const cola = store.models["product.template"].get(5);
        const sourceTable = store.models["restaurant.table"].get(2);
        const destinationTable = store.models["restaurant.table"].get(14);
        const sourceOrder = store.addNewOrder({ table_id: sourceTable });
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 1 }, sourceOrder);

        await store.transferOrder(sourceOrder.uuid, destinationTable);
        const tableOrder = destinationTable.getOrder();
        store.setOrder(tableOrder);

        let destination = null;
        store.navigate = (page, params) => {
            destination = { page, params };
        };

        store.showDefault();

        expect(destination.page).toBe("ProductScreen");
        expect(destination.params.orderUuid).not.toBe(tableOrder.uuid);
        expect(store.getOrder().uuid).not.toBe(tableOrder.uuid);
    });

    test("register config opens product screen", async () => {
        const store = await setupPosEnv();
        store.config.default_screen = "register";
        const order = store.addNewOrder();
        store.setOrder(order);

        const page = store.defaultPage;

        expect(page.page).toBe("ProductScreen");
        expect(page.params.orderUuid).toBe(order.uuid);
    });

    test("timing preset sets slot and non-timing preset clears it", async () => {
        mockDate("2025-06-15 10:00:00");
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const takeawayPreset = store.models["pos.preset"].get(2);
        const eatInPreset = store.models["pos.preset"].get(1);

        store.openPresetTiming = async (targetOrder) => {
            targetOrder.preset_time = DateTime.fromSQL("2025-06-15 12:00:00");
        };

        await store.selectPreset(takeawayPreset, order);
        expect(order.preset_id.id).toBe(takeawayPreset.id);
        expect(order.preset_time.toFormat("HH:mm")).toBe("12:00");

        order.preset_time = DateTime.fromSQL("2025-06-16 11:00:00");
        expect(order.isFutureDate).toBe(true);

        await store.selectPreset(eatInPreset, order);
        expect(order.preset_id.id).toBe(eatInPreset.id);
        expect(order.preset_time).toBe(undefined);
    });

    test("deleting timed table order leaves table empty", async () => {
        mockDate("2025-06-15 10:00:00");
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const cola = store.models["product.template"].get(5);
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 1 }, order);

        order.preset_id = store.models["pos.preset"].get(2);
        order.preset_time = DateTime.fromSQL("2025-06-15 12:20:00");
        store.beforeDeleteOrder = async () => true;

        const deleted = await store.onDeleteOrder(order);

        expect(deleted).toBe(true);
        expect(store.models["pos.order"].getBy("uuid", order.uuid)).toBeEmpty();
        expect(table.getOrders().length).toBe(0);
    });

    test("deleting future order skips preparation cancellation", async () => {
        mockDate("2025-02-12 10:00:00");
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const cola = store.models["product.template"].get(5);
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 1 }, order);
        order.preset_id = store.models["pos.preset"].get(2);
        order.preset_time = DateTime.fromSQL("2025-02-13 15:00:00");

        await store.syncAllOrders({ orders: [order] });
        order.last_order_preparation_change = { lines: { test: {} } };

        let sentPreparationCancelled = 0;
        store.sendOrderInPreparation = async () => {
            sentPreparationCancelled++;
            return true;
        };

        await store.deleteOrders([order]);

        expect(sentPreparationCancelled).toBe(0);
        expect(store.models["pos.order"].getBy("uuid", order.uuid)).toBeEmpty();
    });

    test("findTable falls back to all tables when table is not in current floor", async () => {
        const store = await setupPosEnv();
        const floor = store.models["restaurant.floor"].get(3);
        const tableFromOtherFloor = store.models["restaurant.table"].get(2);
        store.currentFloor = floor;

        const result = store.findTable(String(tableFromOtherFloor.table_number));

        expect(result.id).toBe(tableFromOtherFloor.id);
        expect(result.floor_id.id).not.toBe(floor.id);
    });

    test("ensureGuestCustomerCount sets guest count for preset", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(2);
        const order = store.addNewOrder({ table_id: table });
        const preset = store.models["pos.preset"].get(1);
        preset.use_guest = true;
        await store.selectPreset(preset, order);
        order.uiState.guestSetted = false;

        store.setCustomerCount = async (targetOrder) => {
            targetOrder.setCustomerCount(5);
            return true;
        };

        await store.ensureGuestCustomerCount(order);

        expect(order.getCustomerCount()).toBe(5);
        expect(order.uiState.guestSetted).toBe(true);
    });

    test("table order validates with default preset", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(4);
        const order = store.addNewOrder({ table_id: table });
        const cola = store.models["product.template"].get(5);
        await store.addLineToOrder({ product_tmpl_id: cola, qty: 1 }, order);

        const cashMethod = store.models["pos.payment.method"].find(
            (method) => method.is_cash_count
        );
        order.addPaymentline(cashMethod);
        const validation = new OrderPaymentValidation({
            pos: store,
            orderUuid: order.uuid,
        });

        await validation.validateOrder(true);
        await tick();

        expect(order.preset_id.id).toBe(store.config.default_preset_id.id);
        expect(order.state).toBe("paid");
    });

    test("payment-only order validation skips kitchen send", async () => {
        const store = await setupPosEnv();
        const order = store.addNewOrder();
        const bankMethod = store.models["pos.payment.method"].find(
            (method) => !method.is_cash_count
        );
        order.addPaymentline(bankMethod);
        order.payment_ids[0].setAmount(10);

        let sendPreparationCalls = 0;
        store.sendOrderInPreparation = async () => {
            sendPreparationCalls++;
            return true;
        };

        const validation = new OrderPaymentValidation({
            pos: store,
            orderUuid: order.uuid,
        });

        await validation.validateOrder(true);
        await tick();

        expect(order.state).toBe("paid");
        expect(sendPreparationCalls).toBe(0);
    });

    test("removing table order leaves table without active order", async () => {
        const store = await setupPosEnv();
        const table = store.models["restaurant.table"].get(4);
        const order = store.addNewOrder({ table_id: table });
        const product = store.models["product.template"].get(11);
        await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
        store.router.state.current = "ProductScreen";
        let destination = null;

        store.navigate = (page) => {
            destination = page;
        };

        expect(order.isBooked).toBe(true);
        store.removeOrder(order);
        expect(destination).toBe("FloorScreen");
        expect(table.getOrders().length).toBe(0);
    });

    test("transfer to another floor keeps order lines", async () => {
        const store = await setupPosEnv();
        const sourceTable = store.models["restaurant.table"].get(2);
        const destinationTable = store.models["restaurant.table"].get(14);
        const sourceOrder = store.addNewOrder({ table_id: sourceTable });
        const product = store.models["product.template"].get(5);
        await store.addLineToOrder({ product_tmpl_id: product, qty: 5 }, sourceOrder);

        await store.transferOrder(sourceOrder.uuid, destinationTable);

        expect(sourceOrder.table_id.id).toBe(destinationTable.id);
        expect(sourceOrder.lines).toHaveLength(1);
        expect(sourceOrder.lines[0].qty).toBe(5);
    });

    test("each restaurant floor keeps its own table set", async () => {
        const store = await setupPosEnv();
        const mainFloor = store.models["restaurant.floor"].get(2);
        const patioFloor = store.models["restaurant.floor"].get(3);

        expect(mainFloor.table_ids.map((table) => table.table_number)).toEqual([1, 3, 4]);
        expect(patioFloor.table_ids.map((table) => table.table_number)).toEqual([101, 102, 103]);
    });

    test("selecting child table opens root table order", async () => {
        const store = await setupPosEnv();
        const rootTable = store.models["restaurant.table"].get(2);
        const childTable = store.models["restaurant.table"].get(3);
        childTable.parent_id = rootTable;
        const order = store.addNewOrder({ table_id: rootTable });
        const product = store.models["product.template"].get(6);
        await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);

        await store.setTableFromUi(childTable);

        expect(store.getOrder().table_id.id).toBe(rootTable.id);
        expect(store.getOrder().lines).toHaveLength(1);
        expect(store.getOrder().lines[0].product_id.product_tmpl_id.id).toBe(product.id);
    });

    test("deleting a temporary floor keeps it removed", async () => {
        const store = await setupPosEnv();
        const floorPlan = store.floorPlan;
        floorPlan.startEditMode();

        const ghostFloor = floorPlan.addFloor("Ghost Floor");
        expect(floorPlan.floors.some((floor) => floor.name === "Ghost Floor")).toBe(true);

        const removed = await floorPlan.removeFloor(ghostFloor.uuid);

        expect(removed).toBe(true);
        expect(floorPlan.floors.some((floor) => floor.name === "Ghost Floor")).toBe(false);
    });

    test("table numbers increment per selected floor", async () => {
        const store = await setupPosEnv();
        const floorPlan = store.floorPlan;
        floorPlan.startEditMode();
        const mainFloor = floorPlan.floors.find((floor) => floor.name === "Main Floor");
        const patioFloor = floorPlan.floors.find((floor) => floor.name === "Patio");

        floorPlan.selectFloorByUuid(mainFloor.uuid);
        const nextMainNumber = mainFloor.getMaxTableNumber() + 1;
        const newMainTable = floorPlan.addTable("square");

        floorPlan.selectFloorByUuid(patioFloor.uuid);
        const nextPatioNumber = patioFloor.getMaxTableNumber() + 1;
        const newPatioTable = floorPlan.addTable("square");

        expect(newMainTable.tableNumber).toBe(nextMainNumber);
        expect(newPatioTable.tableNumber).toBe(nextPatioNumber);
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
            expect(order.getOrderlines().length).toBe(1);
        });

        test("do not create second course if use_course_allocation", async () => {
            const store = await setupPosEnv();
            store.config.use_course_allocation = true;

            const order = store.addNewOrder();
            const product = store.models["product.template"].get(5);
            await store.addLineToOrder({ product_tmpl_id: product, qty: 1 }, order);
            const course = store.addCourse();
            expect(order.course_ids.length).toBe(1);
            expect(course.order_id).toBe(order);
            expect(order.getSelectedCourse()).toBe(course);
            expect(order.getOrderlines().length).toBe(1);
        });
    });

    test("preparation receipt order_label", async () => {
        const store = await setupPosEnv();
        const pos_categories = store.models["pos.category"].getAll().map((c) => c.id);

        const order = await getFilledOrder(store);
        const partner = store.models["res.partner"].get(3);
        order.setPartner(partner);
        expect(order.floating_order_name).toBe(partner.name);

        const generator = store.ticketPrinter.getGenerator({ models: store.models, order });
        const orderChange = generator.generatePreparationData(new Set([...pos_categories]), {});
        expect(orderChange[0].extra_data.order_label).toBe(partner.name);

        const table = store.models["restaurant.table"].get(2);
        const tableOrder = await getFilledOrder(store, { table_id: table });
        tableOrder.setPartner(partner);
        const tableGenerator = store.ticketPrinter.getGenerator({
            models: store.models,
            order: tableOrder,
        });
        const tableOrderChange = tableGenerator.generatePreparationData(
            new Set([...pos_categories]),
            {}
        );
        expect(tableOrderChange[0].extra_data.order_label).toBe(`T ${table.table_number}`);
    });
});
