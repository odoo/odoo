import { expect, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

import { OrderWidget } from "@pos_self_order/app/components/order_widget/order_widget";
import { setupSelfPosEnv } from "../utils";
import { definePosSelfModels } from "../data/generate_model_definitions";

definePosSelfModels();

test("OrderWidget renders slot content in the left/right containers", async () => {
    await setupSelfPosEnv();

    class Parent extends Component {
        static template = xml`<OrderWidget>
                <t t-set-slot="left"><button class="my-left-btn">Back</button></t>
                <t t-set-slot="right"><button class="my-right-btn">Pay</button></t>
            </OrderWidget>`;
        static components = { OrderWidget };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);

    expect(".page-buttons .my-left-btn").toHaveCount(1);
    expect(".page-buttons .my-right-btn").toHaveCount(1);
});

test("OrderWidget renders without a slot that is not provided", async () => {
    await setupSelfPosEnv();

    class Parent extends Component {
        static template = xml`<OrderWidget>
                <t t-set-slot="right"><button class="my-right-btn">Pay</button></t>
            </OrderWidget>`;
        static components = { OrderWidget };
        static props = ["*"];
    }

    await mountWithCleanup(Parent);

    expect(".my-right-btn").toHaveCount(1);
    expect(".my-left-btn").toHaveCount(0);
});

test("removeTopClasses controls the border-top class", async () => {
    await setupSelfPosEnv();

    class Parent extends Component {
        static template = xml`<OrderWidget removeTopClasses="this.props.removeTopClasses"/>`;
        static components = { OrderWidget };
        static props = ["*"];
    }

    await mountWithCleanup(Parent, { props: { removeTopClasses: false } });
    expect(".page-buttons").toHaveClass("border-top");
});
