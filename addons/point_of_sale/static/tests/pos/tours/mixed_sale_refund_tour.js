/* global posmodel */
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import { registry } from "@web/core/registry";

/**
 * Orders mixing sale lines (positive quantity) and refund lines (negative quantity).
 * The values computed by the frontend are sent to the backend, which compares them
 * with its own computation (see test_mixed_sale_refund.py).
 *
 * Keep the scenarios in sync with test_mixed_sale_refund.py and mixed_sale_refund.test.js.
 */
const SCENARIOS = [
    {
        name: "net_positive",
        lines: [
            ["Mixed Sale Product", 1],
            ["Mixed Refund Product", -1],
        ],
    },
    {
        name: "net_negative",
        lines: [
            ["Mixed Sale Product", 1],
            ["Mixed Refund Product", -6],
        ],
    },
    {
        name: "pure_refund",
        lines: [["Mixed Refund Product", -6]],
    },
];

const getFrontendData = (order, scenario) => ({
    name: scenario.name,
    uuid: order.uuid,
    is_refund: order.isRefund,
    amount_total: order.priceIncl,
    amount_tax: order.amountTaxes,
    total_due: order.totalDue,
    lines: order.lines.map((line) => ({
        uuid: line.uuid,
        qty: line.qty,
        is_refund: line.qty < 0,
        price_subtotal: line.priceExcl,
        price_subtotal_incl: line.priceIncl,
    })),
});

registry.category("web_tour.tours").add("test_mixed_sale_refund", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),
            {
                content: "Create mixed orders and send the frontend values to the backend",
                trigger: "body",
                run: async () => {
                    const bank = posmodel.config.payment_method_ids.find(
                        (pm) => pm.type === "bank"
                    );
                    const results = [];

                    for (const scenario of SCENARIOS) {
                        const order = posmodel.addNewOrder();
                        for (const [productName, qty] of scenario.lines) {
                            const product = posmodel.models["product.template"].find(
                                (p) => p.name === productName
                            );
                            await posmodel.addLineToOrder({ product_tmpl_id: product, qty }, order);
                        }

                        const data = getFrontendData(order, scenario);
                        order.addPaymentline(bank);
                        data.payment_amount = order.payment_ids.at(-1).amount;
                        data.remaining_due = order.remainingDue;

                        order.setOrderPrices();
                        order.state = "paid";
                        await posmodel.syncAllOrders({ orders: [order] });
                        results.push(data);
                    }

                    await posmodel.data.call("pos.order", "get_mixed_sale_refund_frontend_data", [
                        [],
                        results,
                    ]);
                },
            },
        ].flat(),
});
