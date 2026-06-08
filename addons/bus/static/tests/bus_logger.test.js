import { defineBusModels } from "@bus/../tests/bus_test_helpers";
import { Logger } from "@bus/workers/bus_worker_utils";

import { after, before, describe, expect, test, waitFor } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-dom";

import { contains, getService, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { WebClient } from "@web/webclient/webclient";

defineBusModels();
describe.current.tags("desktop");

before(() => indexedDB.deleteDatabase("test_db"));
after(() => indexedDB.deleteDatabase("test_db"));

test("logs are saved and garbage-collected after TTL", async () => {
    indexedDB.deleteDatabase("test_db");
    const logger = new Logger("test_db");
    await logger.log("foo");
    await logger.log("bar");
    expect(await logger.getLogs()).toEqual(["foo", "bar"]);
    await advanceTime(Logger.LOG_TTL + 1000);
    expect(await logger.getLogs()).toEqual([]);
    indexedDB.deleteDatabase("test_db");
});

test("ask for confirmation downloading logs", async () => {
    odoo.debug = "1";
    await mountWithCleanup(WebClient);
    expect(getService("bus.logs_service").enabled).toBe(null);
    await contains(".o_debug_manager button").click();
    await contains("button[title='Download logs']").click();
    await waitFor(".modal-title:text(You're about to download the bus logs)");
    await waitFor(
        ".modal-body:text(Bus logs contain confidential information and must only be shared with trusted recipients.)"
    );
});
