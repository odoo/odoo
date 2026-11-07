import { Logger } from "@bus/workers/bus_worker_utils";

import { after, before, describe, expect, test } from "@odoo/hoot";
import { advanceTime } from "@odoo/hoot-dom";
import { patchWithCleanup } from "@web/../tests/web_test_helpers";

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

test("getLogs recovers from a closed connection", async () => {
    indexedDB.deleteDatabase("test_db_closed");
    const logger = new Logger("test_db_closed");
    await logger.log("foo");
    patchWithCleanup(indexedDB, {
        open() {
            expect.step("open");
            return super.open(...arguments);
        },
    });
    logger._db.close();
    await Promise.all([logger.log("bar"), logger.log("baz")]);
    expect.verifySteps(["open"]);
    logger._db.close();
    expect(await logger.getLogs()).toEqual(["foo", "bar", "baz"]);
    expect.verifySteps(["open"]);
    logger._db.close();
    indexedDB.deleteDatabase("test_db_closed");
});
