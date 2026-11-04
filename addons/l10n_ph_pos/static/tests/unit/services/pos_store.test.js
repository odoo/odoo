import { describe, expect, test } from "@odoo/hoot";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ConnectionLostError } from "@web/core/network/rpc";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";

definePosModels();

/**
 * A synced order of two lines, and the server's answer for it once its first
 * line was resized and its second one merged into it.
 */
const getSyncedOrder = async (store) => {
    const order = await getFilledOrder(store);
    await store.syncAllOrders();
    const [kept, merged] = order.lines;
    const serverData = { "pos.order.line": [{ ...kept.raw, qty: 5 }] };
    return { order, kept, merged, serverData };
};

const callOrder = async (store, order) => {
    try {
        await store.l10nPhCallOrder(order, "l10n_ph_apply_discount_privileges", []);
    } catch (error) {
        return error;
    }
};

describe("l10n_ph_pos pos_store.js", () => {
    test("merging an order drops the lines the server no longer has", async () => {
        const store = await setupPosEnv();
        const { order, kept, merged, serverData } = await getSyncedOrder(store);
        const unsynced = await store.addLineToOrder(
            { product_tmpl_id: store.models["product.template"].get(8), qty: 1 },
            order
        );

        expect(order.lines).toHaveLength(3);

        store.l10nPhConnectOrderData(order, serverData);

        expect(order.lines).toHaveLength(2);
        expect(order.lines).not.toInclude(merged);
        expect(order.lines).toInclude(unsynced, {
            message: "never synced: not the server's to drop",
        });
        expect(kept.qty).toBe(5);
    });

    describe("a call whose answer never came back", () => {
        test("reads the order again from the server", async () => {
            const store = await setupPosEnv();
            const { order, kept, merged, serverData } = await getSyncedOrder(store);
            const methods = [];
            patchWithCleanup(store.data, {
                async call(model, method) {
                    methods.push(method);
                    if (method === "l10n_ph_apply_discount_privileges") {
                        throw new ConnectionLostError();
                    }
                    return serverData;
                },
            });

            const error = await callOrder(store, order);

            expect(error).toBeInstanceOf(ConnectionLostError);
            expect(error.l10nPhOrderUpToDate).toBe(true);
            expect(methods.filter((method) => method.startsWith("l10n_ph_"))).toEqual([
                "l10n_ph_apply_discount_privileges",
                "l10n_ph_read_discount_privilege_data",
            ]);
            expect(order.lines).not.toInclude(merged);
            expect(kept.qty).toBe(5);
        });

        test("flags the order as stale when it can't be read again", async () => {
            const store = await setupPosEnv();
            const { order, kept } = await getSyncedOrder(store);
            patchWithCleanup(store.data, {
                async call() {
                    throw new ConnectionLostError();
                },
            });

            const error = await callOrder(store, order);

            expect(error).toBeInstanceOf(ConnectionLostError);
            expect(error.l10nPhOrderUpToDate).toBe(false);
            expect(order.lines).toHaveLength(2);
            expect(kept.qty).toBe(3);
        });

        test("is left alone when the server answered with an error", async () => {
            const store = await setupPosEnv();
            const { order } = await getSyncedOrder(store);
            const methods = [];
            patchWithCleanup(store.data, {
                async call(model, method) {
                    methods.push(method);
                    throw Object.assign(new Error("Refused"), { data: { message: "Refused" } });
                },
            });

            const error = await callOrder(store, order);

            expect(error.message).toBe("Refused");
            expect(error.l10nPhOrderUpToDate).toBe(undefined);
            expect(methods.filter((method) => method.startsWith("l10n_ph_"))).toEqual([
                "l10n_ph_apply_discount_privileges",
            ]);
        });
    });
});
