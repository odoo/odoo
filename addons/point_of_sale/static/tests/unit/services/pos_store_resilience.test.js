import { describe, expect, test } from "@odoo/hoot";
import { Deferred } from "@odoo/hoot-mock";

import { definePosModels } from "../data/generate_model_definitions.js";
import { getFilledOrder, setupPosEnv } from "../utils.js";

definePosModels();

test("canceling the customer editor settles without reading an unsaved customer", async () => {
    const store = await setupPosEnv();
    let options;
    store.action = {
        doAction: async (request, args) => {
            options = args;
        },
    };
    store.data.read = () => expect.step("read customer");
    const result = store.editPartner();
    await options.onClose();
    expect(await result).toBe(undefined);
    expect.verifySteps([]);
});

describe("pos_store.js resilience", () => {
    describe("removeOrders", () => {
        test("one failing order does not abort the batch nor throw", async () => {
            const store = await setupPosEnv();
            const order1 = await getFilledOrder(store);
            const order2 = await getFilledOrder(store);
            const order3 = await getFilledOrder(store);
            await store.syncAllOrders({ orders: [order1, order2, order3] });
            expect(order2.isSynced).toBe(true);

            const call = store.data.call.bind(store.data);
            store.data.call = async (model, method, args, kwargs) => {
                if (
                    method === "action_pos_order_cancel" &&
                    args[0].includes(order2.id)
                ) {
                    throw new Error("Order already invoiced");
                }
                return call(model, method, args, kwargs);
            };
            const dialogs = [];
            store.dialog = {
                add: (component, props) => {
                    dialogs.push(props);
                    return () => {};
                },
            };

            const result = await store.removeOrders([order1, order2, order3]);

            expect(result).toBe(false);
            expect(store.models["pos.order"].getBy("uuid", order1.uuid)).toBeEmpty();
            expect(store.models["pos.order"].getBy("uuid", order3.uuid)).toBeEmpty();
            expect(
                store.models["pos.order"].getBy("uuid", order2.uuid),
            ).not.toBeEmpty();
            expect(dialogs).toHaveLength(1);
            expect(dialogs[0].body).toInclude(order2.getName());
        });

        test("a fully successful batch still reports true", async () => {
            const store = await setupPosEnv();
            const order1 = await getFilledOrder(store);
            const order2 = await getFilledOrder(store);
            await store.syncAllOrders({ orders: [order1, order2] });

            expect(await store.removeOrders([order1, order2])).toBe(true);
            expect(store.getOpenOrders()).toHaveLength(0);
        });
    });

    describe("printReceipt", () => {
        test("printing a clean synced order leaves no dirty residue", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);
            await store.syncAllOrders({ orders: [order] });
            order._markClean();
            expect(order.isDirty()).toBe(false);

            store.printer = { print: async () => true };
            await store.printReceipt({ order });

            expect(order.isDirty()).toBe(false);
            expect([...order._dirtyFields]).toEqual([]);
        });

        test("concurrent prints do not lose an increment", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);
            await store.syncAllOrders({ orders: [order] });
            expect(order.nb_print || 0).toBe(0);

            store.printer = { print: async () => true };
            const gate = new Deferred();
            store.data.write = async (model, ids, vals) => {
                await gate;
                const record = store.models[model].get(ids[0]);
                record.update(vals, { omitUnknownField: true });
                return [record];
            };

            const printed = Promise.all([
                store.printReceipt({ order }),
                store.printReceipt({ order }),
            ]);
            gate.resolve();
            await printed;

            expect(order.nb_print).toBe(2);
        });
    });

    describe("handleUrlParams", () => {
        test("a paramless route keeps the selected order", async () => {
            const store = await setupPosEnv();
            const order = await getFilledOrder(store);
            store.setOrder(order);
            expect(store.getOrder().uuid).toBe(order.uuid);

            delete store.router.state.params.orderUuid;
            await store.handleUrlParams();

            expect(store.getOrder()?.uuid).toBe(order.uuid);
        });

        test("a route carrying an orderUuid still selects that order", async () => {
            const store = await setupPosEnv();
            const order1 = await getFilledOrder(store);
            const order2 = await getFilledOrder(store);
            store.setOrder(order1);

            store.router.state.params.orderUuid = order2.uuid;
            await store.handleUrlParams();

            expect(store.getOrder().uuid).toBe(order2.uuid);
        });
    });

    describe("lastPrints", () => {
        const addPreparedLine = async (store, order) => {
            await store.addLineToOrder(
                { product_tmpl_id: store.models["product.template"].get(5), qty: 1 },
                order,
            );
        };

        test("a failed print is not recorded as reprintable", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();
            await addPreparedLine(store, order);
            expect(order.uiState.lastPrints).toHaveLength(0);

            store.printChanges = async () => {
                throw new Error("printer unreachable");
            };
            await store.sendOrderInPreparation(order);

            expect(order.uiState.lastPrints).toHaveLength(0);
        });

        test("the history is bounded", async () => {
            const store = await setupPosEnv();
            const order = store.addNewOrder();
            store.printChanges = async () => true;

            for (let i = 0; i < 14; i++) {
                await addPreparedLine(store, order);
                await store.sendOrderInPreparation(order);
            }

            expect(order.uiState.lastPrints.length).toBeLessThan(14);
            expect(order.uiState.lastPrints).toHaveLength(10);
        });
    });
});
