import { tick } from "@odoo/hoot-dom";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Chrome } from "@point_of_sale/app/pos_app";

export async function mountPosApp(store) {
    store.session.state = "opened";
    store.router.currentScreen.set("FloorScreen");
    store.router.currentScreenParams.set({});
    await mountWithCleanup(Chrome, { props: { disableLoader: () => {} } });
    await tick();
}
