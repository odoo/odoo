import { Logger } from "@bus/workers/bus_worker_utils";

import { after, before, describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-dom";

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
