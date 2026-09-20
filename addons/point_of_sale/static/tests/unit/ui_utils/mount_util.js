import { animationFrame, tick } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Chrome } from "@point_of_sale/app/pos_app";
import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";

export async function mountPosApp(store) {
    store.session.state = "opened";
    await mountWithCleanup(Chrome, { props: { disableLoader: () => {} } });
    await tick();
    await animationFrame();
}

export async function mountProductScreen(store) {
    return mountWithCleanup(ProductScreen, {
        props: { orderUuid: store.getOrder().uuid },
    });
}
