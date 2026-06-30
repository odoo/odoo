import { expirableStorage } from "@im_livechat/core/common/expirable_storage";

import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";
import { asyncStep, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");

test("value is removed from expirable storage after expiration", () => {
    mockDate("2023-01-01 00:00:00");
    const ONE_DAY = 60 * 60 * 24;
    expirableStorage.setItem("foo", "bar", ONE_DAY);
    expect(expirableStorage.getItem("foo")).toBe("bar");
    mockDate("2023-01-01 23:00:00");
    expect(expirableStorage.getItem("foo")).toBe("bar");
    mockDate("2023-01-02 00:00:01");
    expect(expirableStorage.getItem("foo")).toBe(null);
});

test("subscribe/unsubscribe to storage changes", async () => {
    const fooCallback = (value) => asyncStep(`foo - ${value}`);
    const barCallback = (value) => asyncStep(`bar - ${value}`);
    expirableStorage.onChange("foo", fooCallback);
    expirableStorage.onChange("bar", barCallback);
    expirableStorage.setItem("foo", 1);
    await waitForSteps(["foo - 1"]);
    expirableStorage.setItem("bar", 2);
    await waitForSteps(["bar - 2"]);
    expirableStorage.removeItem("foo");
    await waitForSteps(["foo - null"]);
    expirableStorage.offChange("foo", fooCallback);
    expirableStorage.setItem("foo", 3);
    expirableStorage.removeItem("bar");
    await waitForSteps(["bar - null"]);
});
