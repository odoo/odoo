import { expect, getFixture, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    makeMockEnv,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { InstallScopedApp } from "@web/core/install_scoped_app/install_scoped_app";

const mountManifestLink = (href) => {
    const fixture = getFixture();
    const manifestLink = document.createElement("link");
    manifestLink.rel = "manifest";
    manifestLink.href = href;
    fixture.append(manifestLink);
};

test("Installation page displays the app info correctly", async () => {
    const beforeInstallPromptEvent = new CustomEvent("beforeinstallprompt");
    beforeInstallPromptEvent.preventDefault = () => {};
    beforeInstallPromptEvent.prompt = async () => ({ outcome: "accepted" });
    browser.BeforeInstallPromptEvent = beforeInstallPromptEvent;
    await makeMockEnv();
    patchWithCleanup(browser.location, {
        replace: (url) => {
            expect(url.searchParams.get("app_name")).toBe("%3COtto%26", {
                message: "ask to redirect with updated searchParams",
            });
            expect.step("URL replace");
        },
    });
    mountManifestLink("/web/manifest.scoped_app_manifest");
    onRpc("/*", (request) => {
        expect.step(new URL(request.url).pathname);
        return {
            icons: [
                {
                    src: "/fake_image_src",
                    sizes: "any",
                    type: "image/png",
                },
            ],
            name: "My App",
            scope: "/scoped_app/myApp",
            start_url: "/scoped_app/myApp",
        };
    });

    class Parent extends Component {
        static props = ["*"];
        static components = { InstallScopedApp };
        static template = xml`<InstallScopedApp/>`;
    }

    await mountWithCleanup(Parent);
    expect.verifySteps(["/web/manifest.scoped_app_manifest"]);
    await animationFrame();
    expect(".o_install_scoped_app").toHaveCount(1);
    expect(".o_install_scoped_app h1").toHaveText("My App");
    expect(".o_install_scoped_app img").toHaveAttribute("data-src", "/fake_image_src");
    expect(".fa-pencil").toHaveCount(0);
    expect("button.btn-primary").toHaveCount(0);
    expect("div.bg-info").toHaveCount(1);
    expect("div.bg-info").toHaveText("You can install the app from the browser menu");
    browser.dispatchEvent(beforeInstallPromptEvent);
    await animationFrame();
    expect(".fa-pencil").toHaveCount(1);
    expect("div.bg-info").toHaveCount(0);
    expect("button.btn-primary").toHaveCount(1);
    expect("button.btn-primary").toHaveText("Install");
    await contains(".fa-pencil").click();
    await contains("input").edit("<Otto&");
    expect.verifySteps(["URL replace"]);
});

test("Installation page displays the error message when browser is not supported", async () => {
    delete browser.BeforeInstallPromptEvent;
    await makeMockEnv();
    mountManifestLink("/web/manifest.scoped_app_manifest");
    onRpc("/*", (request) => {
        expect.step(new URL(request.url).pathname);
        return {
            icons: [
                {
                    src: "/fake_image_src",
                    sizes: "any",
                    type: "image/png",
                },
            ],
            name: "My App",
            scope: "/scoped_app/myApp",
            start_url: "/scoped_app/myApp",
        };
    });

    class Parent extends Component {
        static props = ["*"];
        static components = { InstallScopedApp };
        static template = xml`<InstallScopedApp/>`;
    }

    await mountWithCleanup(Parent);
    expect.verifySteps(["/web/manifest.scoped_app_manifest"]);
    await animationFrame();
    expect(".o_install_scoped_app").toHaveCount(1);
    expect(".o_install_scoped_app h1").toHaveText("My App");
    expect(".o_install_scoped_app img").toHaveAttribute("data-src", "/fake_image_src");
    expect("button.btn-primary").toHaveCount(0);
    expect("div.bg-info").toHaveCount(1);
    expect("div.bg-info").toHaveText("The app cannot be installed with this browser");
});
