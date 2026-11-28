import { animationFrame, expect, queryOne, runAllTimers, test, waitFor } from "@odoo/hoot";
import { contains, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { TipScreen } from "@point_of_sale/app/screens/tip_screen/tip_screen";
import { CustomerDisplayPlugin } from "@point_of_sale/customer_display/customer_display_plugin";
import { definePosModels } from "../data/generate_model_definitions";
import { getFilledOrder } from "../utils";
import { setupCustomerDisplay } from "./utils";
import { patch } from "@web/core/utils/patch";

definePosModels();

const TERMINAL = ".o_pos_tip_screen";
const DISPLAY = ".o_customer_display_tip_screen";

async function setupTipScreen() {
    const [store, , display] = await setupCustomerDisplay();
    Object.assign(store.config, {
        iface_tipproduct: true,
        set_tip_after_payment: true,
        tip_percentage_1: 10,
        tip_percentage_2: 20,
        tip_percentage_3: 30,
    });
    // Deliver the display's tip actions to the terminal, as the bus would.
    patch(CustomerDisplayPlugin.prototype, {
        async sendAction(type, data) {
            store.customerDisplay._onAction({ type, data });
        },
    });

    // Paid by card as at the till: with tips after payment, it leads to the tip screen.
    const order = await getFilledOrder(store);
    store.setOrder(order);
    order.addPaymentline(store.models["pos.payment.method"].get(2));
    await store.validateOrder();
    expect(store.router.currentScreen()).toBe("TipScreen");

    // The test mounts no POS app: render the screen the router is on.
    patch(TipScreen.prototype, { async printTipReceipt() {} });
    const screen = await mountWithCleanup(TipScreen, {
        props: store.router.currentScreenParams(),
    });
    await waitFor(DISPLAY);
    return { store, order, screen, display };
}

// The customer types without pausing: the amount is not sent to the terminal yet.
const typeOnDisplay = (amount) => contains(`${DISPLAY} input`).edit(amount, { confirm: false });

// A tip above the highest percentage (30%), settled on the display.
async function askLargeTip() {
    await typeOnDisplay("1000");
    await contains(`${DISPLAY} button.settle`).click();
    await waitFor(".modal");
}

test("customer display mirrors the tip screen both ways", async () => {
    const { screen } = await setupTipScreen();
    expect(`${TERMINAL} h2`).toHaveText("Add a tip");
    expect(`${DISPLAY} h2`).toHaveText("Would you like to leave a tip?");
    expect(`${DISPLAY} .percentage-amounts button`).toHaveCount(3);
    expect(`${DISPLAY} button.settle`).not.toBeEnabled();

    // The customer picks a percentage on the display.
    await contains(`${DISPLAY} .percentage-amounts button:contains(20%)`).click();
    await animationFrame();
    expect(screen.state.selectedPercentage).toBe("20%");
    expect(`${DISPLAY} .percentage-amounts button.border-primary`).toHaveText(/20%/);
    expect(`${DISPLAY} button.settle`).toBeEnabled();

    // The cashier changes it on the terminal.
    screen.selectTip(screen.percentageTips[0]);
    await animationFrame();
    expect(`${DISPLAY} .percentage-amounts button.border-primary`).toHaveText(/10%/);

    // The customer types a custom amount instead.
    await typeOnDisplay("5");
    await runAllTimers();
    expect(screen.state.inputTipAmount).toBe("5");
    expect(screen.state.selectedPercentage).toBe(null);
});

test("terminal ignores tip actions for another order or invalid amounts", async () => {
    const { store, order, screen } = await setupTipScreen();
    screen.state.inputTipAmount = "2";

    const sendTip = (data) => store.customerDisplay._onAction({ type: "tip", data });
    sendTip({ orderUuid: "other", action: "input", amount: "9" });
    sendTip({ orderUuid: order.uuid, action: "input", amount: "-1" });
    sendTip({ orderUuid: order.uuid, action: "input", amount: "abc" });
    sendTip({ orderUuid: order.uuid, action: "select", percentage: "99%" });
    // Another type of action, or a malformed message, never reaches the tip screen.
    const otherAction = { orderUuid: order.uuid, action: "input", amount: "9" };
    store.customerDisplay._onAction({ type: "other", data: otherAction });
    store.customerDisplay._onAction(otherAction);
    store.customerDisplay._onAction({ type: "tip", data: null });
    store.customerDisplay._onAction({ type: "tip", data: [] });
    await animationFrame();
    expect(screen.state.inputTipAmount).toBe("2");
});

test("display drops the typed tip when the tip screen closes or changes order", async () => {
    // Display only: on a real till, the terminal has left its tip screen by then.
    const [, , display] = await setupCustomerDisplay();
    const sent = [];
    patch(CustomerDisplayPlugin.prototype, {
        async sendAction(type, data) {
            sent.push(data);
        },
    });
    const showTipScreen = (orderUuid) =>
        display._onDataReceived(
            JSON.stringify({
                tipScreen: {
                    orderUuid,
                    overallAmount: "$ 10.00",
                    tipSubText: "",
                    percentageTips: [{ percentage: "10%", amount: "$ 1.00" }],
                    inputTipAmount: "",
                    selectedPercentage: null,
                    isSettling: false,
                    confirmation: null,
                    currencySymbol: "$",
                },
            })
        );

    showTipScreen("order-a");
    await animationFrame();
    await typeOnDisplay("5");

    // The tip screen closes before the typed amount is sent: it is never sent.
    display._onDataReceived(JSON.stringify({ tipScreen: false }));
    await animationFrame();
    await runAllTimers();
    expect(sent).toEqual([]);

    // The next order's tip screen does not show the previous customer's amount.
    showTipScreen("order-b");
    await animationFrame();
    expect(queryOne(`${DISPLAY} input`).value).toBe("");
    expect(`${DISPLAY} button.settle`).not.toBeEnabled();
});

test("terminal saves No Tip even when the customer's typing arrives meanwhile", async () => {
    const { store, order, screen } = await setupTipScreen();
    // The server answers slowly, as over a real network.
    const written = Promise.withResolvers();
    patch(store.data, {
        async write() {
            await written.promise;
            return super.write(...arguments);
        },
    });

    // The customer keeps raising the amount on the display.
    await typeOnDisplay("1");
    await runAllTimers();
    await typeOnDisplay("12");
    // Meanwhile the cashier picks No Tip on the terminal; the "12" arrives while it saves.
    await contains(`${TERMINAL} button.no-tip`).click();
    await runAllTimers();
    written.resolve();
    await animationFrame();

    expect(order.tip_amount).toBe(0);
    expect(screen.state.inputTipAmount).toBe("0");
});

test("customer settles the tip from the display, only once", async () => {
    const { store, order, screen } = await setupTipScreen();
    let validations = 0;
    patch(screen, {
        async validateTip() {
            validations++;
            return super.validateTip(...arguments);
        },
    });
    expect(store.customerDisplay._buildDisplayPayload(order).tipAmount).toBe(0);

    await contains(`${DISPLAY} .percentage-amounts button:contains(10%)`).click();
    await animationFrame();
    const expectedTip = screen.percentageTips[0].inputTipAmount;
    // The customer taps on the display while the cashier settles on the terminal.
    const settles = [
        screen.onCustomerDisplayAction({ orderUuid: order.uuid, action: "settle" }),
        screen.settle(),
    ];
    await Promise.all(settles);
    await runAllTimers();

    expect(validations).toBe(1);
    expect(order.is_tipped).toBe(true);
    expect(order.tip_amount).toBeCloseTo(expectedTip, { margin: 0.01 });
    const tipProduct = store.config.tip_product_id;
    expect(order.lines.filter((line) => line.product_id.id === tipProduct.id)).toHaveLength(1);

    // The paid screen shows the amount paid, tip included, and the tip on its own.
    const payload = store.customerDisplay._buildDisplayPayload(order);
    expect(payload.paymentAmountInCurrency).toBe(order.paymentAmountInCurrency);
    expect(payload.paymentAmountInCurrency).toInclude(order.totalDue.toFixed(2));
    expect(payload.tipAmount).toInclude(order.tip_amount.toFixed(2));
});

test("large tip confirmation on the display", async () => {
    const { order, screen } = await setupTipScreen();
    await askLargeTip();
    // The customer chose, so the customer confirms, in the same dialog the cashier gets.
    expect(screen.displayConfirmation()).not.toBe(null);
    expect(".modal").toHaveCount(1);
    expect(".modal .modal-title").toHaveText("Are you sure?");
    expect(".modal .modal-body").toHaveText(
        /more than 30% of the order's total amount. Are you sure of this tip amount\?/
    );

    // The customer cancels.
    await contains(".modal button.btn-secondary").click();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(screen.displayConfirmation()).toBe(null);
    expect(order.is_tipped).toBe(false);

    // The cashier changes the amount on the terminal: the pending confirmation is dropped.
    await askLargeTip();
    screen.selectTip(screen.percentageTips[0]);
    await animationFrame();
    await animationFrame();
    expect(".modal").toHaveCount(0);
    expect(screen.state.selectedPercentage).toBe("10%");

    // The customer confirms.
    await askLargeTip();
    await contains(".modal button.btn-primary").click();
    await runAllTimers();
    expect(".modal").toHaveCount(0);
    expect(order.is_tipped).toBe(true);
    expect(order.tip_amount).toBe(1000);
});
