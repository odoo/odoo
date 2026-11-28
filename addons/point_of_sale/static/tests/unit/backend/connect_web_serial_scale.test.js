import { expect, test } from "@odoo/hoot";
import { click } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { ConnectWebSerialScale } from "@point_of_sale/backend/connect_web_serial_scale/connect_web_serial_scale";
import { WebSerialScale } from "@point_of_sale/app/utils/scale/web_serial_scale";
import { definePosModels } from "../data/generate_model_definitions";
import { setupPosEnv } from "../utils";

definePosModels();

const CONNECTED = ".text-success:contains(Scale connected)";

async function mountWidget(serial) {
    patchWithCleanup(navigator, { serial });
    await setupPosEnv();
    await mountWithCleanup(ConnectWebSerialScale, { props: { record: {} } });
    await animationFrame();
}

test("updates on disconnect and reconnect", async () => {
    const port = { connected: true };
    const serial = Object.assign(new EventTarget(), { getPorts: async () => [port] });
    await mountWidget(serial);
    expect(CONNECTED).toHaveCount(1);

    port.connected = false;
    serial.dispatchEvent(new Event("disconnect"));
    await animationFrame();
    expect(CONNECTED).toHaveCount(0);

    port.connected = true;
    serial.dispatchEvent(new Event("connect"));
    await animationFrame();
    expect(CONNECTED).toHaveCount(1);
});

test("shows 'Scale connected' after connecting a compatible scale", async () => {
    const ports = [];
    const port = { connected: true, close: async () => {} };
    const serial = Object.assign(new EventTarget(), {
        getPorts: async () => ports,
        requestPort: async () => {
            ports.push(port);
            return port;
        },
    });
    patchWithCleanup(WebSerialScale.prototype, { isScaleSupported: async () => true });
    await mountWidget(serial);
    expect(CONNECTED).toHaveCount(0);

    await click("button");
    await animationFrame();
    expect(CONNECTED).toHaveCount(1);
});
