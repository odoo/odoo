// @ts-check

import { expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, Deferred } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";
import {
    contains,
    getService,
    makeMockEnv,
    mountWebClient,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { registry } from "@web/core/registry";
import { watchServiceWorkerUpdates } from "@web/webclient/service_worker_service";
import { WebClient } from "@web/webclient/webclient";

test("can be rendered", async () => {
    await mountWebClient();

    expect(`header > nav.o_main_navbar`).toHaveCount(1);
});

test("can render a main component", async () => {
    class MyComponent extends Component {
        static props = {};
        static template = xml`<span class="chocolate">MyComponent</span>`;
    }

    const env = await makeMockEnv();
    registry.category("main_components").add("mycomponent", { Component: MyComponent });

    await mountWebClient({ env });

    expect(`.chocolate`).toHaveCount(1);
});

test.tags("desktop");
test("control-click <a href/> in a standalone component", async () => {
    class MyComponent extends Component {
        static props = {};
        static template = xml`<a href="#" class="MyComponent" t-on-click="this.onclick">Some link</a>`;

        /** @param {MouseEvent} ev */
        onclick(ev) {
            expect.step(ev.ctrlKey ? "ctrl-click" : "click");
            ev.preventDefault();
        }
    }

    await mountWithCleanup(MyComponent);

    expect.verifySteps([]);

    await contains(".MyComponent").click();
    await contains(".MyComponent").click({ ctrlKey: true });

    expect.verifySteps(["click", "ctrl-click"]);
});

test.tags("desktop");
test("control-click propagation stopped on <a href/>", async () => {
    expect.assertions(3);

    patchWithCleanup(WebClient.prototype, {
        /** @param {MouseEvent} ev */
        onGlobalClick(ev) {
            super.onGlobalClick(ev);
            if (ev.ctrlKey) {
                expect(ev.defaultPrevented).toBe(false, {
                    message:
                        "the global click should not prevent the default behavior on ctrl-click an <a href/>",
                });
                ev.preventDefault();
            }
        },
    });

    class MyComponent extends Component {
        static props = {};
        static template = xml`<a href="#" class="MyComponent" t-on-click="this.onclick">Some link</a>`;

        /** @param {MouseEvent} ev */
        onclick(ev) {
            expect.step(ev.ctrlKey ? "ctrl-click" : "click");
            ev.preventDefault();
        }
    }

    await mountWebClient();

    registry.category("main_components").add("mycomponent", { Component: MyComponent });
    await animationFrame();

    expect.verifySteps([]);

    await contains(".MyComponent").click();
    await contains(".MyComponent").click({ ctrlKey: true });

    expect.verifySteps(["click"]);
});

class MockServiceWorker extends EventTarget {
    /** @param {string} state */
    constructor(state) {
        super();
        this.state = state;
    }

    /** @param {{ type: string }} message */
    postMessage(message) {
        expect.step(`postMessage:${message.type}`);
    }

    /** @param {string} state */
    setState(state) {
        this.state = state;
        this.dispatchEvent(new Event("statechange"));
    }
}

class MockRegistration extends EventTarget {
    /** @type {MockServiceWorker | null} */
    active = null;
    /** @type {MockServiceWorker | null} */
    installing = null;
    /** @type {MockServiceWorker | null} */
    waiting = null;

    update() {
        expect.step("update");
        return Promise.resolve();
    }
}

/** @returns {Array<() => void>} */
function captureVisibilityHandlers() {
    /** @type {Array<() => void>} */
    const handlers = [];
    patchWithCleanup(browser, {
        addEventListener(type, handler) {
            expect(type).toBe("visibilitychange");
            handlers.push(() => {
                const event = new Event(type);
                if (typeof handler === "function") {
                    handler.call(window, event);
                } else {
                    handler.handleEvent(event);
                }
            });
        },
    });
    return handlers;
}

test("SW update: posts SKIP_WAITING when an updated worker finishes installing", async () => {
    captureVisibilityHandlers();
    const registration = new MockRegistration();
    registration.active = new MockServiceWorker("activated");
    watchServiceWorkerUpdates(/** @type {any} */ (registration));
    expect.verifySteps([]);

    registration.installing = new MockServiceWorker("installing");
    registration.dispatchEvent(new Event("updatefound"));
    expect.verifySteps([]);

    registration.installing.setState("installed");
    expect.verifySteps(["postMessage:SKIP_WAITING"]);

    registration.installing.setState("activating");
    registration.installing.setState("activated");
    expect.verifySteps([]);
});

test("SW update: first install keeps the natural lifecycle (no SKIP_WAITING)", async () => {
    captureVisibilityHandlers();
    const registration = new MockRegistration();
    watchServiceWorkerUpdates(/** @type {any} */ (registration));

    registration.installing = new MockServiceWorker("installing");
    registration.dispatchEvent(new Event("updatefound"));
    registration.installing.setState("installed");
    expect.verifySteps([]);
});

test("SW update: a worker already waiting at boot is promoted immediately", async () => {
    captureVisibilityHandlers();
    const registration = new MockRegistration();
    registration.active = new MockServiceWorker("activated");
    registration.waiting = new MockServiceWorker("installed");
    watchServiceWorkerUpdates(/** @type {any} */ (registration));
    expect.verifySteps(["postMessage:SKIP_WAITING"]);
});

test("SW update: periodic and visibility-triggered registration.update()", async () => {
    const visibilityHandlers = captureVisibilityHandlers();
    const registration = new MockRegistration();
    registration.active = new MockServiceWorker("activated");
    watchServiceWorkerUpdates(/** @type {any} */ (registration));
    expect(visibilityHandlers).toHaveLength(1);
    expect.verifySteps([]);

    const SIX_HOURS = 6 * 60 * 60 * 1000;
    await advanceTime(SIX_HOURS);
    expect.verifySteps(["update"]);
    await advanceTime(SIX_HOURS);
    expect.verifySteps(["update"]);

    visibilityHandlers[0]();
    expect.verifySteps(["update"]);
});

test.tags("desktop");
test("the default landing is the home menu even with a dangling first menu id", async () => {
    const def = new Deferred();
    onRpc("/web/webclient/load_menus", () => def);
    browser.localStorage.webclient_menus_version =
        "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0:7";
    browser.localStorage.webclient_menus = JSON.stringify({
        2: { appID: 2, children: [], name: "Real App", id: 2, actionID: 1001 },
        root: { id: "root", name: "root", appID: "root", children: [999, 2] },
    });

    await makeMockEnv();
    /** @type {any[]} */
    const selected = [];
    patchWithCleanup(getService("menu"), {
        selectMenu: async (menu) => {
            selected.push(menu?.id ?? menu);
        },
    });

    await mountWebClient();
    await animationFrame();

    expect(selected).toEqual([]);
    expect(".o_home_menu").toHaveCount(1);
    expect(".o_home_menu .o_app").toHaveCount(1);
    def.resolve();
});

test("SW update: the returned disposer stops the interval and the visibility hook", async () => {
    const visibilityHandlers = captureVisibilityHandlers();
    const registration = new MockRegistration();
    registration.active = new MockServiceWorker("activated");
    const dispose = watchServiceWorkerUpdates(/** @type {any} */ (registration));
    expect(visibilityHandlers).toHaveLength(1);

    const SIX_HOURS = 6 * 60 * 60 * 1000;
    await advanceTime(SIX_HOURS);
    expect.verifySteps(["update"]);

    dispose();
    await advanceTime(SIX_HOURS);
    expect.verifySteps([]);

    registration.installing = new MockServiceWorker("installing");
    registration.dispatchEvent(new Event("updatefound"));
    registration.installing.setState("installed");
    expect.verifySteps([]);
});
