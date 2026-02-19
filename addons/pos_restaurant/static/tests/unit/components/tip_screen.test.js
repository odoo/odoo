import { test, expect } from "@odoo/hoot";
import { TipScreen } from "@point_of_sale/app/screens/tip_screen/tip_screen";
import { mountWithCleanup, MockServer } from "@web/../tests/web_test_helpers";
import { setupPosEnv, getFilledOrder } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";

definePosModels();

async function setupScreen(inputTip = null, selectedPercentage = null) {
    const store = await setupPosEnv();
    const order = await getFilledOrder(store);
    const cardPaymentMethod = store.models["pos.payment.method"].get(2);
    order.addPaymentline(cardPaymentMethod);
    await store.syncAllOrders();

    const screen = await mountWithCleanup(TipScreen, {
        props: { orderUuid: order.uuid },
    });

    if (inputTip !== null) {
        screen.state.inputTipAmount = inputTip;
    }
    if (selectedPercentage !== null) {
        screen.state.selectedPercentage = selectedPercentage;
    }

    return { store, order, screen };
}

test("validateTip", async () => {
    const { store, order, screen } = await setupScreen("2");
    TipScreen.prototype.printTipReceipt = async () => {};
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
});

test("tipAmount", async () => {
    const { screen } = await setupScreen();
    screen.state.inputTipAmount = "5.50";
    expect(screen.tipAmount).toBe(5.5);
    screen.state.inputTipAmount = "invalid";
    expect(screen.tipAmount).toBe(0);
});

test("overallAmount", async () => {
    const { screen } = await setupScreen("5.50");
    const expected = screen.env.utils.formatCurrency(screen.totalAmount + 5.5);
    expect(screen.overallAmount).toBe(expected);
});

test("tipSubText", async () => {
    const { screen } = await setupScreen(null, "15%");
    expect(screen.tipSubText).toBe("Includes a 15% tip");

    screen.state.selectedPercentage = null;
    screen.state.inputTipAmount = "5.50";
    expect(screen.tipSubText).toBe(
        "With " + screen.env.utils.formatCurrency(5.5) + " tip Included"
    );

    screen.state.inputTipAmount = "";
    expect(screen.tipSubText).toBe("");
});

test("canSettle", async () => {
    const { screen } = await setupScreen(null, "15%");
    expect(screen.canSettle).toBe(true);

    screen.state.selectedPercentage = null;
    screen.state.inputTipAmount = "5.50";
    expect(screen.canSettle).toBe(true);

    screen.state.inputTipAmount = "";
    expect(screen.canSettle).toBe(false);
});

test("selectTip", async () => {
    const { screen } = await setupScreen();
    const tip = { percentage: "15%", amount: 5.5 };

    screen.selectTip(tip);
    expect(screen.state.selectedPercentage).toBe("15%");
    expect(screen.state.inputTipAmount).toBe(screen.env.utils.formatCurrency(5.5, false));

    screen.selectTip(null);
    expect(screen.state.selectedPercentage).toBe(null);
    expect(screen.state.inputTipAmount).toBe("0");
});
