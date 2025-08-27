import { describe, test, expect } from "@odoo/hoot";
import { TipScreen } from "@pos_restaurant/app/screens/tip_screen/tip_screen";
import { mountWithCleanup, MockServer } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

describe("tip_screen.js", () => {
    test("validateTip", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const cardPaymentMethod = store.models["pos.payment.method"].get(2);
        order.addPaymentline(cardPaymentMethod);
        await store.syncAllOrders();
        TipScreen.prototype.printTipReceipt = async () => {};
        const screen = await mountWithCleanup(TipScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        screen.state.inputTipAmount = "2";
        await screen.validateTip();
        expect(order.is_tipped).toBe(true);
        expect(order.tip_amount).toBe(2);
        const tipLine = order.lines.find(
            (line) => line.product_id.id === store.config.tip_product_id.id
        );
        store.data.write("pos.order.line", [tipLine.id], {
            write_date: luxon.DateTime.now(),
        });
        MockServer.env["pos.order.line"].write([tipLine.id], {
            order_id: order.id,
            write_date: luxon.DateTime.now(),
        });
        expect(Boolean(tipLine)).toBe(true);
        expect(tipLine.price_unit).toBe(2);
        await store.removeOrder(order);
    });

    test("overallAmountStr", async () => {
        const store = await setupPosEnv();
        const order = await getFilledOrder(store);
        const cardPaymentMethod = store.models["pos.payment.method"].get(2);
        order.addPaymentline(cardPaymentMethod);
        await store.syncAllOrders();
        TipScreen.prototype.printTipReceipt = async () => {};
        const screen = await mountWithCleanup(TipScreen, {
            props: {
                orderUuid: order.uuid,
            },
        });
        screen.state.inputTipAmount = "2";
        const result = screen.overallAmountStr;
        const total = order.getTotalWithTax();
        const original = screen.env.utils.formatCurrency(total);
        const tip = screen.env.utils.formatCurrency(2);
        const overall = screen.env.utils.formatCurrency(total + 2);
        expect(result).toBe(`${original} + ${tip} tip = ${overall}`);
    });
});
