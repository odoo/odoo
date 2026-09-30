import { describe, expect, test } from "@odoo/hoot";
import {
    asyncStep,
    makeMockEnv,
    restoreRegistry,
    waitForSteps,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

describe.current.tags("desktop");

test("multi tab allow to share values between tabs", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    firstTabEnv.services.legacy_multi_tab.setSharedValue("foo", 1);
    expect(secondTabEnv.services.legacy_multi_tab.getSharedValue("foo")).toBe(1);
    firstTabEnv.services.legacy_multi_tab.setSharedValue("foo", 2);
    expect(secondTabEnv.services.legacy_multi_tab.getSharedValue("foo")).toBe(2);
    firstTabEnv.services.legacy_multi_tab.removeSharedValue("foo");
    expect(secondTabEnv.services.legacy_multi_tab.getSharedValue("foo")).toBe(undefined);
});

test("multi tab triggers shared_value_updated", async () => {
    const firstTabEnv = await makeMockEnv();
    restoreRegistry(registry);
    const secondTabEnv = await makeMockEnv(null, { makeNew: true });
    secondTabEnv.services.legacy_multi_tab.bus.addEventListener(
        "shared_value_updated",
        ({ detail }) => {
            asyncStep(`${detail.key} - ${JSON.parse(detail.newValue)}`);
        }
    );
    firstTabEnv.services.legacy_multi_tab.setSharedValue("foo", "bar");
    firstTabEnv.services.legacy_multi_tab.setSharedValue("foo", "foo");
    firstTabEnv.services.legacy_multi_tab.removeSharedValue("foo");
    await waitForSteps(["foo - bar", "foo - foo", "foo - null"]);
});
