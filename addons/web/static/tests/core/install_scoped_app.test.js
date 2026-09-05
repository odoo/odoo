import { animationFrame, expect, getFixture, test } from "@odoo/hoot";
import { Component, xml } from "@odoo/owl";
import { contains, makeTestApp, mountWithCleanup, onRpc } from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { InstallScopedApp } from "@web/core/install_scoped_app/install_scoped_app";
import { patch } from "@web/core/utils/patch";

const mountManifestLink = (href) => {
    const fixture = getFixture();
    const manifestLink = document.createElement("link");
    manifestLink.rel = "manifest";
    manifestLink.href = href;
    fixture.append(manifestLink);
};

class BeforeInstallPromptEvent extends Event {
    async prompt() {
        return { outcome: "accepted" };
    }
}

test("Installation page displays the app info correctly", async () => {
    patch(browser, { BeforeInstallPromptEvent });
    patch(browser.location, {
        replace: (url) => {
            expect(url.searchParams.get("app_name")).toBe("%3COtto%26", {
                message: "ask to redirect with updated searchParams",
            });
            expect.step("URL replace");
        },
    });
    await makeTestApp();
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
        static components = { InstallScopedApp };
        static template = xml`<InstallScopedApp/>`;
    }

    await mountWithCleanup(Parent);
    expect.verifySteps(["/web/manifest.scoped_app_manifest"]);
    await animationFrame();
    expect(".o_install_scoped_app").toHaveCount(1);
    expect(".o_install_scoped_app h1").toHaveText("My App");
    expect(".o_install_scoped_app img").toHaveAttribute("data-src", "/fake_image_src");
    expect("[data-icon='edit']").toHaveCount(0);
    expect("button.btn-primary").toHaveCount(0);
    expect("div.bg-info").toHaveCount(1);
    expect("div.bg-info").toHaveText("You can install the app from the browser menu");
    browser.dispatchEvent(new BeforeInstallPromptEvent("beforeinstallprompt"));
    await animationFrame();
    expect("[data-icon='edit']").toHaveCount(1);
    expect("div.bg-info").toHaveCount(0);
    expect("button.btn-primary").toHaveCount(1);
    expect("button.btn-primary").toHaveText("Install");
    await contains("[data-icon='edit']").click();
    await contains("input").edit("<Otto&", { confirm: "blur" });
    expect.verifySteps(["URL replace"]);
});

test("Installation page displays the error message when browser is not supported", async () => {
    patch(browser, { BeforeInstallPromptEvent: undefined });
    await makeTestApp();
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
