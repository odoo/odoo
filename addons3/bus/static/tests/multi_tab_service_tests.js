/** @odoo-module **/

import { addBusServicesToRegistry } from "@bus/../tests/helpers/test_utils";

import { browser } from "@web/core/browser/browser";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { patchWithCleanup, nextTick } from "@web/../tests/helpers/utils";

QUnit.module("multi_tab_service_tests.js");

QUnit.test("multi tab service elects new master on pagehide", async function (assert) {
    addBusServicesToRegistry();
    const firstTabEnv = await makeTestEnv();
    assert.ok(firstTabEnv.services["multi_tab"].isOnMainTab(), "only tab should be the main one");

    // prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName === "pagehide") {
                return;
            }
            super.addEventListener(eventName, callback);
        },
    });
    const secondTabEnv = await makeTestEnv();
    firstTabEnv.services["multi_tab"].bus.addEventListener("no_longer_main_tab", () =>
        assert.step("tab1 no_longer_main_tab")
    );
    secondTabEnv.services["multi_tab"].bus.addEventListener("no_longer_main_tab", () =>
        assert.step("tab2 no_longer_main_tab")
    );
    window.dispatchEvent(new Event("pagehide"));

    // Let the multi tab elect a new main.
    await nextTick();
    assert.notOk(firstTabEnv.services["multi_tab"].isOnMainTab());
    assert.ok(secondTabEnv.services["multi_tab"].isOnMainTab());
    assert.verifySteps(["tab1 no_longer_main_tab"]);
});

QUnit.test("multi tab allow to share values between tabs", async function (assert) {
    addBusServicesToRegistry();
    const firstTabEnv = await makeTestEnv();
    const secondTabEnv = await makeTestEnv();

    firstTabEnv.services["multi_tab"].setSharedValue("foo", 1);
    assert.deepEqual(secondTabEnv.services["multi_tab"].getSharedValue("foo"), 1);
    firstTabEnv.services["multi_tab"].setSharedValue("foo", 2);
    assert.deepEqual(secondTabEnv.services["multi_tab"].getSharedValue("foo"), 2);

    firstTabEnv.services["multi_tab"].removeSharedValue("foo");
    assert.notOk(secondTabEnv.services["multi_tab"].getSharedValue("foo"));
});

QUnit.test("multi tab triggers shared_value_updated", async function (assert) {
    addBusServicesToRegistry();
    const firstTabEnv = await makeTestEnv();
    const secondTabEnv = await makeTestEnv();

    secondTabEnv.services["multi_tab"].bus.addEventListener(
        "shared_value_updated",
        ({ detail }) => {
            assert.step(`${detail.key} - ${JSON.parse(detail.newValue)}`);
        }
    );
    firstTabEnv.services["multi_tab"].setSharedValue("foo", "bar");
    firstTabEnv.services["multi_tab"].setSharedValue("foo", "foo");
    firstTabEnv.services["multi_tab"].removeSharedValue("foo");

    await nextTick();
    assert.verifySteps(["foo - bar", "foo - foo", "foo - null"]);
});

QUnit.test("multi tab triggers become_master", async function (assert) {
    addBusServicesToRegistry();
    await makeTestEnv();
    // prevent second tab from receiving pagehide event.
    patchWithCleanup(browser, {
        addEventListener(eventName, callback) {
            if (eventName === "pagehide") {
                return;
            }
            super.addEventListener(eventName, callback);
        },
    });
    const secondTabEnv = await makeTestEnv();
    secondTabEnv.services["multi_tab"].bus.addEventListener("become_main_tab", () =>
        assert.step("become_main_tab")
    );
    window.dispatchEvent(new Event("pagehide"));

    // Let the multi tab elect a new main.
    await nextTick();
    assert.verifySteps(["become_main_tab"]);
});
