import { test, expect, animationFrame } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup, contains } from "@web/../tests/web_test_helpers";
import { setupPosEnv } from "../utils";
import { definePosModels } from "../data/generate_model_definitions";
import { PaymentMethodBreakdown } from "@point_of_sale/app/components/payment_method_breakdown/payment_method_breakdown";

definePosModels();

test("Nested payment breakdowns", async () => {
    await setupPosEnv();
    const props = {
        title: "DEMO 1",
        total_amount: 21,
        transactions: [
            { id: 1, name: "DEMO-1-1", amount: 101 },
            { id: 2, name: "DEMO-1-2", amount: 202 },
        ],
    };
    // Wrap the component in a parent so mutating the (reactive) props triggers
    // real prop updates, allowing us to verify recursive payment breakdowns.
    class Wrapper extends Component {
        static template = xml`<PaymentMethodBreakdown t-props="this.childProps"/>`;
        static components = { PaymentMethodBreakdown };
        setup() {
            this.childProps = props;
        }
    }
    await mountWithCleanup(Wrapper);
    contains(".accordion-header:contains(DEMO 1)").click();
    expect(".accordion-content div:contains(DEMO-1-1 $ 101.00)").toBeDisplayed();
    expect(".accordion-content div:contains(DEMO-1-2 $ 202.00)").toBeDisplayed();

    // Second level of nested transactions.
    props.transactions[1].subTransactions = [
        { id: 11, name: "SUB-DEMO-1", amount: 2001 },
        { id: 12, name: "SUB-DEMO-2", amount: 2002 },
    ];
    await animationFrame();
    await contains("div .accordion-header:contains(DEMO-1-2)").click();
    expect(".accordion-content div:contains(SUB-DEMO-1 $ 2,001.00)").toBeDisplayed();
    expect(".accordion-content div:contains(SUB-DEMO-2 $ 2,002.00)").toBeDisplayed();

    // Third level of nested transactions.
    props.transactions[1].subTransactions[0].subTransactions = [
        { id: 21, name: "SUPER-SUB-DEMO-1", amount: 20001 },
        { id: 22, name: "SUPER-SUB-DEMO-2", amount: 20002 },
    ];
    await animationFrame();
    await contains("div .accordion-header:contains(DEMO-1-2)").click();
    await contains("div .accordion-header:contains(SUB-DEMO-1)").click();
    expect(".accordion-content div:contains(SUPER-SUB-DEMO-1 $ 20,001.00)").toBeDisplayed();
    expect(".accordion-content div:contains(SUPER-SUB-DEMO-2 $ 20,002.00)").toBeDisplayed();
});
