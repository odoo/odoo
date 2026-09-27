import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    getService,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { rpcBus } from "@web/core/network/rpc";
import { config as transitionConfig } from "@web/core/transition";
import { LoadingIndicator } from "@web/webclient/loading_indicator/loading_indicator";

const payload = (id) => ({ data: { id, params: { model: "", method: "" } }, settings: {} });

beforeEach(() => {
    patchWithCleanup(transitionConfig, { disabled: true });
});

test("displays the loading indicator", async () => {
    await mountWithCleanup(LoadingIndicator, { noMainContainer: true });
    expect(".o_loading_indicator").toHaveCount(0, {
        message: "the loading indicator should not be displayed",
    });
    rpcBus.trigger("RPC:REQUEST", payload(1));
    await runAllTimers();
    await animationFrame();
    expect(".o_loading_indicator").toHaveCount(1, {
        message: "the loading indicator should be displayed",
    });
    expect(".o_loading_indicator").toHaveText("Loading…", {
        message: "the loading indicator should display 'Loading'",
    });
    rpcBus.trigger("RPC:RESPONSE", payload(1));
    await runAllTimers();
    await animationFrame();
    expect(".o_loading_indicator").toHaveCount(0, {
        message: "the loading indicator should not be displayed",
    });
});

test("loading indicator is not displayed immediately", async () => {
    await mountWithCleanup(LoadingIndicator, { noMainContainer: true });
    const ui = getService("ui");
    ui.bus.addEventListener("BLOCK", () => {
        expect.step("block");
    });
    ui.bus.addEventListener("UNBLOCK", () => {
        expect.step("unblock");
    });
    rpcBus.trigger("RPC:REQUEST", payload(1));
    await animationFrame();
    expect(".o_loading_indicator").toHaveCount(0);
    await advanceTime(400);
    expect(".o_loading_indicator").toHaveCount(1);
    rpcBus.trigger("RPC:RESPONSE", payload(1));
    await animationFrame();
    expect(".o_loading_indicator").toHaveCount(0);
});
