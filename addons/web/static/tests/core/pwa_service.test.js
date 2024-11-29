import { describe, expect, getFixture, test } from "@odoo/hoot";
import { mockFetch } from "@odoo/hoot-mock";
import { getService, makeMockEnv, patchWithCleanup } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";

describe.current.tags("headless");

const mountManifestLink = (href) => {
    const fixture = getFixture();
    const manifestLink = document.createElement("link");
    manifestLink.rel = "manifest";
    manifestLink.href = href;
    fixture.append(manifestLink);
};

test("PWA service fetches the manifest found in the page", async () => {
    await makeMockEnv();
    mountManifestLink("/web/manifest.webmanifest");
    mockFetch((route) => {
        expect.step(route);
        return { name: "Odoo PWA" };
    });
    const pwaService = await getService("pwa");
    let appManifest = await pwaService.getManifest();
    expect(appManifest).toEqual({ name: "Odoo PWA" });
    expect.verifySteps(["/web/manifest.webmanifest"]);
    appManifest = await pwaService.getManifest();
    expect(appManifest).toEqual({ name: "Odoo PWA" });
    // manifest is only fetched once to get the app name
    expect.verifySteps([]);
});

test("PWA installation process", async () => {
    const beforeInstallPromptEvent = new CustomEvent("beforeinstallprompt");
    beforeInstallPromptEvent.preventDefault = () => {};
    beforeInstallPromptEvent.prompt = async () => ({ outcome: "accepted" });
    browser.BeforeInstallPromptEvent = beforeInstallPromptEvent;
    await makeMockEnv();
    mountManifestLink("/web/manifest.scoped_app_manifest");
    mockFetch((route) => {
        expect.step(route);
        return { name: "My App", scope: "/scoped_app/myApp", start_url: "/scoped_app/myApp" };
    });
    patchWithCleanup(browser.localStorage, {
        setItem(key, value) {
            if (key === "pwaService.installationState") {
                expect.step(value);
                return null;
            }
            return super.setItem(key, value);
        },
    });
    const pwaService = await getService("pwa");
    expect(pwaService.isAvailable).toBe(false);
    expect(pwaService.canPromptToInstall).toBe(false);
    browser.dispatchEvent(beforeInstallPromptEvent);
    expect(pwaService.isAvailable).toBe(true);
    expect(pwaService.canPromptToInstall).toBe(true);
    await pwaService.show({
        onDone: (res) => {
            expect.step("onDone call with installation " + res.outcome);
        },
    });
    expect(pwaService.canPromptToInstall).toBe(false);
    expect.verifySteps(['{"/odoo":"accepted"}', "onDone call with installation accepted"]);
});
