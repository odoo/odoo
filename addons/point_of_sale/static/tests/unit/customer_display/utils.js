import { expect, runAllTimers, waitFor } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";
import { CustomerDisplayService } from "@point_of_sale/customer_display/customer_display_service";
import { setupPosEnv } from "../utils";
import { PosRouter } from "@point_of_sale/app/services/pos_router_service";

const waitAndExpect = async (trigger, count = 1) => {
    await waitFor(trigger);
    expect(trigger).toHaveCount(count);
};

export const CustomerDisplayAssertions = {
    waitAndExpect,
    hasOrderLine: async ({
        productName,
        price,
        quantity,
        priceUnit,
        withClass = "",
        withoutClass,
    }) => {
        let trigger = `li.o_customer_display_orderline${withClass}`;
        if (withoutClass) {
            trigger += `:not(${withoutClass})`;
        }
        if (productName) {
            trigger += `:has(.product-name:contains(${productName}))`;
        }
        if (price) {
            trigger += `:has(.product-price:contains(${price}))`;
        }
        if (quantity) {
            trigger += `:has(.qty:contains("${quantity}"))`;
        }
        if (priceUnit) {
            trigger += `:has(.price-per-unit:contains("${priceUnit}"))`;
        }
        await waitAndExpect(trigger);
    },
    hasPaymentLine: async (name, amount) => {
        let trigger = `.o_customer_display_payment_line:has(div:contains(${name}))`;
        if (amount) {
            trigger += `:has(div:contains('${amount}'))`;
        }
        await waitAndExpect(trigger);
    },
    hasOrderlineCount: async (count) => {
        await runAllTimers();
        expect("li.o_customer_display_orderline").toHaveCount(count);
    },

    checkWelcome: async () => await waitAndExpect("h1:contains('Welcome')"),
    checkThankyou: async () => await waitAndExpect(".feedback-summary"),
    checkScreenSaver: async () => await waitAndExpect("div.login-overlay"),
};

const mockCustomerDisplayConnection = () => {
    // Mock customer display message delivery without relying on a real connection
    patchWithCleanup(CustomerDisplayService.prototype, {
        send(payload) {
            const payloadStr = JSON.stringify(payload);
            this._onDataReceived(payloadStr);
        },
    });
};
const mockPosRouterNavigation = () => {
    // Simulate router navigation without modifying the browser URL
    patchWithCleanup(PosRouter.prototype, {
        navigate(routeName, routeParams) {
            this.state.current = routeName;
            this.state.params = routeParams;
        },
    });
};

export const setupCustomerDisplay = async () => {
    mockCustomerDisplayConnection();
    mockPosRouterNavigation();
    const store = await setupPosEnv();
    store.router.state.current = "ProductScreen";
    await mountWithCleanup(CustomerDisplay);

    const order = store.addNewOrder();
    store.setOrder(order);
    await CustomerDisplayAssertions.checkWelcome();
    return [store, order];
};
