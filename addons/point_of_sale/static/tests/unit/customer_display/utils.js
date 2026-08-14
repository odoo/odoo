import { expect, runAllTimers, waitFor } from "@odoo/hoot";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { CustomerDisplay } from "@point_of_sale/customer_display/customer_display";
import { CustomerDisplayTerminalPlugin } from "@point_of_sale/app/plugins/customer_display_terminal_plugin";
import { setupPosEnv } from "../utils";

export const CustomerDisplayAssertions = {
    async waitAndExpect(selector, count = 1) {
        await waitFor(selector);
        expect(selector).toHaveCount(count);
    },

    async hasOrderLine({ productName, price, quantity, priceUnit, withClass = "", withoutClass }) {
        let selector = `li.o_customer_display_orderline${withClass}`;
        if (withoutClass) {
            selector += `:not(${withoutClass})`;
        }
        if (productName) {
            selector += `:has(.product-name:contains(${productName}))`;
        }
        if (price) {
            selector += `:has(.product-price:contains(${price}))`;
        }
        if (quantity) {
            selector += `:has(.qty:contains("${quantity}"))`;
        }
        if (priceUnit) {
            selector += `:has(.price-per-unit:contains("${priceUnit}"))`;
        }
        await this.waitAndExpect(selector);
    },

    async hasPaymentLine(name, amount) {
        let selector = `.o_customer_display_payment_line:has(div:contains(${name}))`;
        if (amount) {
            selector += `:has(div:contains('${amount}'))`;
        }
        await this.waitAndExpect(selector);
    },

    async hasOrderlineCount(count) {
        await runAllTimers();
        expect("li.o_customer_display_orderline").toHaveCount(count);
    },

    async hasTotal({ total, subtotal, taxes, changes }) {
        const totalSelector = (name, amount) =>
            `.o_customer_display_total:has(div.row:contains(${name} $ ${amount}))`;
        await this.waitAndExpect(totalSelector("Total", total));
        subtotal && expect(totalSelector("Subtotal", subtotal)).toBeDisplayed();
        taxes && expect(totalSelector("Taxes", taxes)).toBeDisplayed();
        changes && expect(totalSelector("Changes", changes)).toBeDisplayed();
    },

    async checkWelcome() {
        await this.waitAndExpect("h1:contains('Welcome')");
    },
    async checkThankyou() {
        await this.waitAndExpect(".feedback-summary");
    },
    async checkScreenSaver() {
        await this.waitAndExpect("div.login-overlay");
    },
};

const mockCustomerDisplayConnection = (display) => {
    // Deliver the payload without relying on a real connection. The terminal and
    // the display hold two distinct BroadcastChannel objects, so a message posted
    // by one does reach the other within the same context.
    patchWithCleanup(CustomerDisplayTerminalPlugin.prototype, {
        send(payload) {
            display._onDataReceived(JSON.stringify(payload));
        },
        // Nothing announces itself over a mocked connection, so consider the
        // mounted display connected.
        get hasConnectedDisplay() {
            return true;
        },
    });
};

export const setupCustomerDisplay = async () => {
    const store = await setupPosEnv();
    store.router.currentScreen.set("ProductScreen");
    const display = await mountWithCleanup(CustomerDisplay);
    mockCustomerDisplayConnection(display.customerDisplay);

    const order = store.addNewOrder();
    store.setOrder(order);
    await CustomerDisplayAssertions.checkWelcome();
    return [store, order, display.customerDisplay];
};
