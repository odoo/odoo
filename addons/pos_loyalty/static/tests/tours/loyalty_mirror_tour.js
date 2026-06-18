/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as PaymentScreen from "@point_of_sale/../tests/pos/tours/utils/payment_screen_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as TicketScreen from "@point_of_sale/../tests/pos/tours/utils/ticket_screen_util";
import * as FeedbackScreen from "@point_of_sale/../tests/pos/tours/utils/feedback_screen_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("test_loyalty_mirror", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            ProductScreen.clickDisplayedProduct("Mirror Product A"),
            ProductScreen.clickDisplayedProduct("Mirror Product A"),
            ProductScreen.clickDisplayedProduct("Mirror Product B"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true),
            {
                content: "Compute the frontend loyalty data and throw it to the backend",
                trigger: "body",
                run: async () => {
                    const order = posmodel.getOrder();
                    if (!order.applyCode("MIRROR10").success) {
                        throw new Error("MIRROR10 code was rejected");
                    }
                    order.setOrderPrices();
                    order.state = "paid";
                    await posmodel.syncAllOrders({ orders: [order] });

                    const lines = order.getOrderlines();
                    const data = {};
                    for (const rule of posmodel.models["loyalty.rule"].getAll()) {
                        data[rule.id] = {
                            qualifying: rule
                                ._qualifyingLines(order)
                                .map((line) => line.uuid)
                                .sort(),
                            fulfilled: rule.isFulfilled(order),
                            points: rule.getPoints(order),
                            lines: Object.fromEntries(
                                lines.map((line) => [
                                    line.uuid,
                                    [rule._inDomain(line), rule._countsForPoints(line)],
                                ])
                            ),
                        };
                    }
                    try {
                        await posmodel.data.call("pos.order", "get_frontend_loyalty_mirror_data", [
                            [order.id],
                            data,
                        ]);
                    } finally {
                        // Ignore any error, the main test is in the backend
                    }
                },
            },
        ].flat(),
});

const captureRewardCostsStep = {
    content: "Capture the frontend reward costs, then sync and send them to the backend",
    trigger: "body",
    run: async () => {
        const order = posmodel.getOrder();
        order.setOrderPrices();
        const costs = {};
        for (const line of order.getOrderlines()) {
            if (line.is_reward_line) {
                costs[line.uuid] = line.points_cost;
            }
        }
        order.state = "paid";
        await posmodel.syncAllOrders({ orders: [order] });
        try {
            await posmodel.data.call("pos.order", "get_frontend_loyalty_cost_mirror_data", [
                [order.id],
                costs,
            ]);
        } finally {
            // Ignore any error, the assertions live in the backend.
        }
    },
};

registry.category("web_tour.tours").add("test_loyalty_mirror_reward_cost", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // 3 units earn 30 points (unit rule), enough to auto-claim the per-point discount.
            ProductScreen.clickDisplayedProduct("Mirror Cost Product"),
            ProductScreen.clickDisplayedProduct("Mirror Cost Product"),
            ProductScreen.clickDisplayedProduct("Mirror Cost Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true),
            captureRewardCostsStep,
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_mirror_reward_cost_overspend", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // 1 unit earns 100 points but the $10 order only absorbs a 10-point discount,
            // so the per-point reward is capped: it must cost 10 points, not 100.
            ProductScreen.clickDisplayedProduct("Mirror Overspend Product"),
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank", true),
            captureRewardCostsStep,
        ].flat(),
});

registry.category("web_tour.tours").add("test_loyalty_mirror_refund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            // A nominative program only banks points to a customer's card, so set one: that
            // is what makes the backend record the loyalty.history the reversal reads back.
            ProductScreen.clickPartnerButton(),
            ProductScreen.clickCustomer("Partner Test 1"),
            ProductScreen.clickDisplayedProduct("Mirror Refund Product"),
            // Pay the full amount: clicking the method fills the whole remaining due.
            ProductScreen.clickPayButton(),
            PaymentScreen.clickPaymentMethod("Bank"),
            PaymentScreen.clickValidate(),
            FeedbackScreen.isShown(),
            FeedbackScreen.clickNextOrder(),
            // Refund the whole order.
            ProductScreen.clickRefund(),
            TicketScreen.filterIs("Paid"),
            TicketScreen.selectOrder("001"),
            ProductScreen.clickNumpad("1"),
            TicketScreen.confirmRefund(),
            PaymentScreen.clickPaymentMethod("Bank", true),
            {
                content:
                    "Compute the frontend refund reversal, then sync and send it to the backend",
                trigger: "body",
                run: async () => {
                    const refund = posmodel.getOrder();
                    refund.setOrderPrices();
                    const data = {};
                    for (const program of posmodel.models["loyalty.program"].getAll()) {
                        data[program.id] = program._getRefundReversalPoints(refund);
                    }
                    refund.state = "paid";
                    await posmodel.syncAllOrders({ orders: [refund] });
                    try {
                        await posmodel.data.call(
                            "pos.order",
                            "get_frontend_loyalty_refund_mirror_data",
                            [[refund.id], data]
                        );
                    } finally {
                        // Ignore any error, the assertions live in the backend.
                    }
                },
            },
        ].flat(),
});
