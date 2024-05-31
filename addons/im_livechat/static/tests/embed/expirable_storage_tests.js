/* @odoo-module */

import { expirableStorage } from "@im_livechat/embed/core/misc";

import { patchDate } from "@web/../tests/helpers/utils";

QUnit.module("expirable storage");

QUnit.test("expire after a said amount of time ", async (assert) => {
    const KEY = "my_storage_key";
    const ONE_DAY = 60 * 60 * 24;
    patchDate(2020, 2, 1, 10, 0, 0);
    expirableStorage.setItem(KEY, "hello world", ONE_DAY);
    assert.equal(expirableStorage.getItem(KEY), "hello world");
    patchDate(2020, 2, 2, 11, 0, 0); // next day (one hour later to make sure it expires)
    assert.equal(expirableStorage.getItem(KEY), null);
});
