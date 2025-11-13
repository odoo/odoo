import { expirableStorage } from "@im_livechat/core/common/expirable_storage";

import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

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
    const fooCallback = (value) => expect.step(`foo - ${value}`);
    const barCallback = (value) => expect.step(`bar - ${value}`);
    expirableStorage.onChange("foo", fooCallback);
    expirableStorage.onChange("bar", barCallback);
    expirableStorage.setItem("foo", 1);
    await expect.waitForSteps(["foo - 1"]);
    expirableStorage.setItem("bar", 2);
    await expect.waitForSteps(["bar - 2"]);
    expirableStorage.removeItem("foo");
    await expect.waitForSteps(["foo - null"]);
    expirableStorage.offChange("foo", fooCallback);
    expirableStorage.setItem("foo", 3);
    expirableStorage.removeItem("bar");
    await expect.waitForSteps(["bar - null"]);
});
