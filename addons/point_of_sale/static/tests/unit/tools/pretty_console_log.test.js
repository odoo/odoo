import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

import { Logger } from "@bus/workers/bus_worker_utils";
import { logPosMessage } from "@point_of_sale/app/utils/pretty_console_log";

test("a failing log write does not raise an error", async () => {
    patchWithCleanup(Logger.prototype, {
        async log() {
            expect.step("log");
            throw new Error("The database connection is closing.");
        },
    });
    patchWithCleanup(console, {
        warn: () => expect.step("warn"),
    });
    logPosMessage("IndexedDB", "test", "message");
    await animationFrame();
    expect.verifySteps(["log", "warn"]);
});
