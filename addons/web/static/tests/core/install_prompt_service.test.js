/** @odoo-module */

import { makeMockEnv, getService } from "@web/../tests/web_test_helpers";
import { mockFetch } from "@odoo/hoot-mock";
import { after, expect, test, beforeEach } from "@odoo/hoot";

let installPrompt;

beforeEach(async () => {
    await makeMockEnv();
    installPrompt = await getService("installPrompt");
});

test.tags("headless")("install prompt fetch the application name", async () => {
    const restoreFetch = mockFetch((route) => {
        expect.step(route);
        return new Response('{"name": "Odoo PWA"}', { status: 200 });
    });
    after(restoreFetch);
    let appName = await installPrompt.getAppName();
    expect(appName).toBe("Odoo PWA");
    expect(["/web/manifest.webmanifest"]).toVerifySteps();

    appName = await installPrompt.getAppName();
    expect(appName).toBe("Odoo PWA");
    expect([], {
        message: "the manifest is only fetched once to get the app name",
    }).toVerifySteps();
});
