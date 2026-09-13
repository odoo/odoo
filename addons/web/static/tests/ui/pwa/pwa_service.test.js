// @ts-check

import { after, describe, expect, getFixture, test } from "@odoo/hoot";
import { Deferred, microTick } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    getService,
    makeMockEnv,
    mockService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { useService } from "@web/core/utils/hooks";
import { pwaService } from "@web/ui/pwa/pwa_service";

describe.current.tags("headless");

const mountManifestLink = (/** @type {string} */ href) => {
    const fixture = getFixture();
    const manifestLink = document.createElement("link");
    manifestLink.rel = "manifest";
    manifestLink.href = href;
    fixture.append(manifestLink);
};

test("PWA service fetches the manifest found in the page", async () => {
    await makeMockEnv();
    mountManifestLink("/web/manifest.webmanifest");
    onRpc("/*", (request) => {
        expect.step(new URL(request.url).pathname);
        return { name: "Odoo PWA" };
    });
    const pwaService = await getService("pwa");
    let appManifest = await pwaService.getManifest();
    expect(appManifest).toEqual({ name: "Odoo PWA" });
    expect.verifySteps(["/web/manifest.webmanifest"]);
    appManifest = await pwaService.getManifest();
    expect(appManifest).toEqual({ name: "Odoo PWA" });
    expect.verifySteps([]);
});

test("PWA installation process", async () => {
    const beforeInstallPromptEvent = Object.assign(
        new CustomEvent("beforeinstallprompt"),
        {
            prompt: async () => ({ outcome: "accepted" }),
        },
    );
    beforeInstallPromptEvent.preventDefault = () => {};
    beforeInstallPromptEvent.prompt = async () => ({ outcome: "accepted" });
    browser.BeforeInstallPromptEvent = beforeInstallPromptEvent;
    await makeMockEnv();
    mountManifestLink("/web/manifest.scoped_app_manifest");
    onRpc("/*", (request) => {
        expect.step(new URL(request.url).pathname);
        return {
            name: "My App",
            scope: "/scoped_app/myApp",
            start_url: "/scoped_app/myApp",
        };
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
    expect.verifySteps([
        '{"/odoo":"accepted"}',
        "onDone call with installation accepted",
    ]);
});

test("Safari install prompt: dismissal persists on every dialog close path", async () => {
    patchWithCleanup(browser.navigator, {
        userAgent:
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    });
    mockService("dialog", {
        add(_component, _props, options) {
            expect.step("dialog opened");
            options.onClose();
            return async () => {};
        },
    });
    await makeMockEnv();
    const pwaService = await getService("pwa");
    expect(pwaService.isAvailable).toBe(true);
    expect(pwaService.canPromptToInstall).toBe(true);

    await pwaService.show({
        onDone: () => expect.step("onDone"),
    });
    expect.verifySteps(["dialog opened", "onDone"]);
    expect(pwaService.canPromptToInstall).toBe(false);
    expect(
        JSON.parse(browser.localStorage.getItem("pwaService.installationState")),
    ).toEqual({ "/odoo": "dismissed" });
});

test("PWA service boots despite a corrupted installationState in localStorage", async () => {
    await makeMockEnv();
    browser.localStorage.setItem("pwaService.installationState", "{ not json");
    const pwaService = await getService("pwa");
    expect(typeof pwaService.getManifest).toBe("function");
    expect(pwaService.isAvailable).toBe(false);
});

test("a native prompt is consumed once, so a second show() cannot reject", async () => {
    let prompts = 0;
    const beforeInstallPromptEvent = Object.assign(
        new CustomEvent("beforeinstallprompt"),
        {
            prompt: async () => ({ outcome: "accepted" }),
        },
    );
    beforeInstallPromptEvent.preventDefault = () => {};
    beforeInstallPromptEvent.prompt = async () => {
        if (++prompts > 1) {
            throw new DOMException("already prompted", "InvalidStateError");
        }
        return { outcome: "accepted" };
    };
    browser.BeforeInstallPromptEvent = beforeInstallPromptEvent;
    await makeMockEnv();
    const pwaService = await getService("pwa");
    browser.dispatchEvent(beforeInstallPromptEvent);

    await pwaService.show();
    await pwaService.show();
    expect(prompts).toBe(1);
});

test("concurrent getManifest() callers share a single fetch", async () => {
    await makeMockEnv();
    mountManifestLink("/web/manifest.webmanifest");
    let fetches = 0;
    onRpc("/*", () => {
        fetches++;
        return { name: "Odoo PWA" };
    });
    const pwaService = await getService("pwa");
    const [a, b, c] = await Promise.all([
        pwaService.getManifest(),
        pwaService.getManifest(),
        pwaService.getManifest(),
    ]);
    expect(fetches).toBe(1);
    expect(a).toEqual({ name: "Odoo PWA" });
    expect(b).toEqual(a);
    expect(c).toEqual(a);
});

test("a failed manifest fetch is retried rather than memoised forever", async () => {
    await makeMockEnv();
    mountManifestLink("/web/manifest.webmanifest");
    let attempts = 0;
    onRpc("/*", () => {
        if (++attempts === 1) {
            throw new Error("offline");
        }
        return { name: "Odoo PWA" };
    });
    const pwaService = await getService("pwa");
    await expect(pwaService.getManifest()).rejects.toThrow();
    expect(await pwaService.getManifest()).toEqual({ name: "Odoo PWA" });
    expect(attempts).toBe(2);
});

test("a native prompt that rejects leaves no install affordance behind", async () => {
    const beforeInstallPromptEvent = new Event("beforeinstallprompt");
    /** @type {any} */ (beforeInstallPromptEvent).prompt = () =>
        Promise.reject(new Error("prompt() may only be called once"));
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    await makeMockEnv();
    const pwaService = await getService("pwa");
    browser.dispatchEvent(beforeInstallPromptEvent);
    expect(pwaService.canPromptToInstall).toBe(true);

    await expect(pwaService.show()).rejects.toThrow();

    expect(pwaService.nativePrompt).toBe(null);
    expect(pwaService.canPromptToInstall).toBe(false);
});

test("two live services share a native prompt and consume it only once", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    const env = await makeMockEnv();
    const first = getService("pwa");
    const second = pwaService.start(env, { dialog: getService("dialog") });
    after(() => second.destroy());
    const event = Object.assign(new Event("beforeinstallprompt"), {
        prompt: async () => {
            expect.step("prompt");
            return { outcome: "accepted" };
        },
    });
    browser.dispatchEvent(event);
    expect(first.canPromptToInstall).toBe(true);
    expect(second.canPromptToInstall).toBe(true);
    await Promise.all([first.show(), second.show()]);
    expect(first.canPromptToInstall).toBe(false);
    expect(second.canPromptToInstall).toBe(false);
    expect(first.isAvailable).toBe(false);
    expect(second.isAvailable).toBe(false);
    expect.verifySteps(["prompt"]);
});

test("destroying the newest service does not silence a surviving service", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    const env = await makeMockEnv();
    const first = getService("pwa");
    const second = pwaService.start(env, { dialog: getService("dialog") });
    second.destroy();
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: async () => ({ outcome: "accepted" }),
        }),
    );
    expect(first.canPromptToInstall).toBe(true);
    expect(second.canPromptToInstall).toBe(false);
});

test("an older prompt completion cannot hide a newer prompt", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    await makeMockEnv();
    const service = getService("pwa");
    const outcome = new Deferred();
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: () => outcome,
        }),
    );
    const showing = service.show();
    const newer = Object.assign(new Event("beforeinstallprompt"), {
        prompt: async () => ({ outcome: "accepted" }),
    });
    browser.dispatchEvent(newer);
    outcome.resolve({ outcome: "dismissed" });
    await showing;
    expect(service.nativePrompt).toBe(newer);
    expect(service.canPromptToInstall).toBe(true);
});

test("destroying a service releases its unused native prompt", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    await makeMockEnv();
    const service = getService("pwa");
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: async () => {
                expect.step("prompt");
                return { outcome: "accepted" };
            },
        }),
    );
    service.destroy();
    await service.show();
    expect(service.nativePrompt).toBe(null);
    expect(service.canPromptToInstall).toBe(false);
    expect(service.isAvailable).toBe(false);
    expect.verifySteps([]);
});

test("Safari dismissal survives a throwing completion callback", async () => {
    patchWithCleanup(browser.navigator, {
        userAgent:
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    });
    /** @type {() => void} */
    let close;
    mockService("dialog", {
        add(_component, _props, options) {
            close = async () => options.onClose();
            return async () => {};
        },
    });
    await makeMockEnv();
    const service = getService("pwa");
    await service.show({
        onDone: () => {
            throw new Error("consumer failure");
        },
    });
    await expect(close()).rejects.toThrow("consumer failure");
    expect(service.canPromptToInstall).toBe(false);
    expect(service.hasScopeBeenInstalled("/odoo")).toBe(false);
    expect(
        JSON.parse(browser.localStorage.getItem("pwaService.installationState")),
    ).toEqual({ "/odoo": "dismissed" });
});

test("late subscribers inherit only an unconsumed prompt", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    const env = await makeMockEnv();
    const first = getService("pwa");
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: async () => ({ outcome: "accepted" }),
        }),
    );
    const second = pwaService.start(env, { dialog: getService("dialog") });
    after(() => second.destroy());
    expect(second.canPromptToInstall).toBe(true);
    await first.show();
    const third = pwaService.start(env, { dialog: getService("dialog") });
    after(() => third.destroy());
    expect(third.canPromptToInstall).toBe(false);
    expect(third.isAvailable).toBe(false);
    expect(second.canPromptToInstall).toBe(false);
});

test("show waits for the native prompt's asynchronous completion callback", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    await makeMockEnv();
    const service = getService("pwa");
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: async () => ({ outcome: "accepted" }),
        }),
    );
    const done = new Deferred();
    let settled = false;
    const showing = service.show({ onDone: () => done }).then(() => {
        settled = true;
    });
    await microTick();
    await microTick();
    expect(settled).toBe(false);
    done.resolve();
    await showing;
    expect(settled).toBe(true);
});

test("declining an app synchronizes its live services without dismissing another scope", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    const env = await makeMockEnv();
    const first = getService("pwa");
    const second = pwaService.start(env, { dialog: getService("dialog") });
    const otherScope = pwaService.start(env, { dialog: getService("dialog") });
    otherScope.startUrl = "/scoped_app/other";
    after(() => second.destroy());
    after(() => otherScope.destroy());
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: async () => ({ outcome: "accepted" }),
        }),
    );
    first.decline();
    expect(first.canPromptToInstall).toBe(false);
    expect(second.canPromptToInstall).toBe(false);
    expect(otherScope.canPromptToInstall).toBe(true);
    expect(second.isAvailable).toBe(true);
});

test("destroying PWA through a component's service view removes its subscription", async () => {
    patchWithCleanup(browser, { BeforeInstallPromptEvent: Event });
    class Owner extends Component {
        static template = xml`<div/>`;
        static props = {};
        setup() {
            this.pwa = useService("pwa");
        }
    }
    const owner = await mountWithCleanup(Owner);
    owner.pwa.destroy();
    browser.dispatchEvent(
        Object.assign(new Event("beforeinstallprompt"), {
            prompt: async () => ({ outcome: "accepted" }),
        }),
    );
    expect(getService("pwa").canPromptToInstall).toBe(false);
    expect(getService("pwa").isAvailable).toBe(false);
});
