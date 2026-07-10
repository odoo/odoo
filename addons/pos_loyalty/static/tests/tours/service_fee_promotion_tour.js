import * as ProductScreen from "@point_of_sale/../tests/pos/tours/utils/product_screen_util";
import * as Dialog from "@point_of_sale/../tests/generic_helpers/dialog_util";
import * as Chrome from "@point_of_sale/../tests/pos/tours/utils/chrome_util";
import * as Order from "@point_of_sale/../tests/generic_helpers/order_widget_util";
import { registry } from "@web/core/registry";

registry.category("web_tour.tours").add("ServiceFeePromotionTour", {
    steps: () =>
        [
            Chrome.startPoS(),
            Dialog.confirm("Open Register"),

            // An automatic order discount (10% off, service fee included in its base)
            // applies on top of a fixed service fee that spans two tax groups (two fee
            // lines). Editing the fee quantity must still scale the whole fee and not
            // revert it to the default price while the promotion recomputes.
            ProductScreen.clickDisplayedProduct("Big Item"),
            ProductScreen.clickDisplayedProduct("Small Item"),
            Order.hasServiceFee("5.00"), // $10 fee split evenly over the two tax groups.

            // Scale the fixed fee to quantity 3 -> $30.00 total ($15.00 per fee line).
            ProductScreen.clickLine("Service Fee", "1"),
            ProductScreen.clickNumpad("3"),
            {
                content: "DIAGNOSTIC: wait then dump order state",
                trigger: "body",
                run: async () => {
                    // eslint-disable-next-line no-undef
                    const order = posmodel.getOrder();
                    const dump = () =>
                        order.lines.map((l) => ({
                            product: l.product_id.display_name,
                            qty: l.qty,
                            price_unit: l.price_unit,
                            sfq: l.extra_tax_data?.service_fee_qty,
                            isFee: l.isServiceFeeLine(),
                            isReward: l.is_reward_line,
                        }));
                    console.log("DIAG t0", JSON.stringify(dump()));
                    await new Promise((r) => setTimeout(r, 2000));
                    console.log("DIAG t2000", JSON.stringify(dump()));
                },
            },
        ].flat(),
});
