/** @odoo-module */

import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { getService, makeMockEnv } from "@web/../tests/web_test_helpers";

describe.current.tags("headless");

beforeEach(makeMockEnv);

test("install prompt fetch the application name", async () => {
    mockFetch((route) => {
        expect.step(route);
        return { name: "Odoo PWA" };
    });

    let appName = await getService("installPrompt").getAppName();
    expect(appName).toBe("Odoo PWA");
    expect(["/web/manifest.webmanifest"]).toVerifySteps();

    appName = await getService("installPrompt").getAppName();
    expect(appName).toBe("Odoo PWA");
    expect([], {
        message: "the manifest is only fetched once to get the app name",
    }).toVerifySteps();
});
