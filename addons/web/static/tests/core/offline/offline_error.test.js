import { ConnectionLostError } from "@web/core/network/rpc";

import { animationFrame, expect, test } from "@odoo/hoot";
import { makeMockEnv } from "@web/../tests/web_test_helpers";

test("ConnectionLostError handler", async () => {
    expect.errors(1);

    const env = await makeMockEnv();
    expect(env.services.offline.offline).toBe(false);
    const error = new ConnectionLostError("/fake_url");
    Promise.reject(error);
    await animationFrame();
    expect(env.services.offline.offline).toBe(true);
    expect.verifyErrors([
        `Error: Connection to "/fake_url" couldn't be established or was interrupted`,
    ]);
});
