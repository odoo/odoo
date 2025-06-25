import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";

import { describe, expect, test } from "@odoo/hoot";
import { mockDate } from "@odoo/hoot-mock";

describe.current.tags("desktop");

test("value is removed from expirable storage after expiration", async () => {
    mockDate("2023-01-01 00:00:00");
    const ONE_DAY = 60 * 60 * 24;
    expirableStorage.setItem("foo", "bar", ONE_DAY);
    expect(expirableStorage.getItem("foo")).toBe("bar");
    mockDate("2023-01-01 23:00:00");
    expect(expirableStorage.getItem("foo")).toBe("bar");
    mockDate("2023-01-02 00:00:01");
    expect(expirableStorage.getItem("foo")).toBe(null);
});
