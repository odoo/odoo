/* @odoo-module */

import { expirableStorage } from "@im_livechat/embed/common/expirable_storage";
import { patchDate } from "@web/../tests/helpers/utils";

QUnit.test("value is removed from expirable storage after expiration", async () => {
    patchDate(2023, 1, 1, 0, 0, 0);
    const ONE_DAY = 60 * 60 * 24;
    expirableStorage.setItem("foo", "bar", ONE_DAY);
    expect(expirableStorage.getItem("foo")).toBe("bar");
    patchDate(2023, 1, 1, 23, 0, 0);
    expect(expirableStorage.getItem("foo")).toBe("bar");
    patchDate(2023, 1, 2, 0, 0, 1);
    expect(expirableStorage.getItem("foo")).toBe(null);
});
