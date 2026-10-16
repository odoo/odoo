import { expect, mockUserAgent, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { patch } from "@web/core/utils/patch";
import { createPaymentLine, getFilledOrder, setupPosEnv } from "@point_of_sale/../tests/unit/utils";
import { definePosModels } from "@point_of_sale/../tests/unit/data/generate_model_definitions";
import { useVivaApp } from "@pos_viva_com/app/hooks/use_viva_app";

definePosModels();

class Host extends Component {
    static template = xml`<div/>`;
    setup() {
        this.vivaApp = useVivaApp(() => {});
    }
}

test("the Viva.com app is opened with its options and the payment callback", async () => {
    mockUserAgent("android");
    const store = await setupPosEnv();
    const viva = store.models["pos.payment.method"].get(2);
    viva.payment_provider = "viva_com";
    const order = await getFilledOrder(store);
    store.setOrder(order);
    const opened = [];
    patch(window, { open: (url) => opened.push(url) });
    const host = await mountWithCleanup(Host);

    await host.vivaApp.start(viva);

    expect(opened).toHaveLength(1);
    expect(opened[0]).toInclude(
        `&show_receipt=true&show_transaction_result=true&show_rating=true&callback=${window.location.origin}/pos_viva_com/${store.config.id}/payment/${order.uuid}&`
    );
});

test("retrying a Viva.com app payment opens the app again for the same line", async () => {
    mockUserAgent("android");
    const store = await setupPosEnv();
    const viva = store.models["pos.payment.method"].get(2);
    viva.payment_provider = "viva_com";
    const order = await getFilledOrder(store);
    store.setOrder(order);
    const line = createPaymentLine(store, order, viva, { payment_status: "error" });
    const opened = [];
    patch(window, { open: (url) => opened.push(url) });
    const host = await mountWithCleanup(Host);

    await host.vivaApp.retry(line);

    expect(order.payment_ids).toEqual([line]);
    expect(line.getPaymentStatus()).toBe("waitingCard");
    expect(opened).toHaveLength(1);
    expect(opened[0]).toInclude(`&clientTransactionId=${line.viva_com_session_id}&`);
});
