import { ConnectionLostError } from "@web/core/network/rpc";

import { animationFrame, expect, test } from "@odoo/hoot";
import { getService, makeMockEnv } from "@web/../tests/web_test_helpers";

test("ConnectionLostError handler", async () => {
    expect.errors(1);

    await makeMockEnv();
    expect(getService("offline").offline).toBe(false);
    const error = new ConnectionLostError("/fake_url");
    Promise.reject(error);
    await animationFrame();
    expect(getService("offline").offline).toBe(true);
    expect.verifyErrors([
        `Error: Connection to "/fake_url" couldn't be established or was interrupted`,
    ]);
});
