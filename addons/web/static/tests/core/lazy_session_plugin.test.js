import { Component, onMounted, onWillStart, Plugin, useProps, usePlugin, xml } from "@odoo/owl";
import { after, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import {
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { registry } from "@web/core/registry";
import { services } from "@web/core/services";
import { WebClient } from "@web/webclient/webclient";
import { LazySessionPlugin } from "@web/webclient/lazy_session_plugin";

test("Only call once session info data when services calls lazy session", async () => {
    patchWithCleanup(WebClient.prototype, {
        setup() {
            super.setup();
            onMounted(() => expect.step("web_client_mounted"));
        },
    });
    onRpc("lazy_session_info", () => {
        expect.step("load_session_info");
        return { a: "a", b: "b" };
    });

    class FakeAPlugin extends Plugin {
        lazySession = usePlugin(LazySessionPlugin);
        setup() {
            expect.step("service_a_before");
            this.lazySession.getValue("a", (value) => {
                expect(value).toBe("a");
                expect.step("session_a_after_lazy");
            });
            expect.step("service_a_after");
        }
    }
    services.add(FakeAPlugin);
    after(() => services.delete(FakeAPlugin));
    class FakeBPlugin extends Plugin {
        lazySession = usePlugin(LazySessionPlugin);
        setup() {
            expect.step("service_b_before");
            this.lazySession.getValue("b", (value) => {
                expect(value).toBe("b");
                expect.step("session_b_after_lazy");
            });
            expect.step("service_b_after");
        }
    }
    services.add(FakeBPlugin);
    after(() => services.delete(FakeBPlugin));

    await mountWithCleanup(WebClient);
    await animationFrame();
    expect.verifySteps([
        "service_a_before",
        "service_a_after",
        "service_b_before",
        "service_b_after",
        "web_client_mounted",
        "load_session_info", // <= only do it once after webclient is mounted
        "session_a_after_lazy",
        "session_b_after_lazy",
    ]);
});

test("Only call once lazy session info data on action", async () => {
    patchWithCleanup(WebClient.prototype, {
        setup() {
            super.setup();
            onMounted(() => expect.step("web_client_mounted"));
        },
    });
    onRpc("lazy_session_info", () => {
        expect.step("load_session_info");
        return { a: "a" };
    });
    const actionRegistry = registry.category("actions");
    class TestClientAction extends Component {
        static template = xml`<div/>`;
        props = useProps();
        setup() {
            expect.step("myaction_before");
            this.lazySession = usePlugin(LazySessionPlugin);
            onWillStart(() => {
                expect.step("myaction_on_will_start");
                this.lazySession.getValue("a", (value) => {
                    expect(value).toEqual("a");
                    expect.step("myaction_on_will_start_after");
                });
            });
        }
    }
    actionRegistry.add("__test__client__action__", TestClientAction);

    await mountWithCleanup(WebClient);
    await animationFrame();
    await getService("action").doAction({
        tag: "__test__client__action__",
        type: "ir.actions.client",
    });
    await animationFrame();
    await getService("action").doAction({
        tag: "__test__client__action__",
        type: "ir.actions.client",
    });
    await animationFrame();
    expect.verifySteps([
        "web_client_mounted",
        "myaction_before",
        "myaction_on_will_start",
        "load_session_info", // <= only do it once after webclient is mounted
        "myaction_on_will_start_after",
        "myaction_before",
        "myaction_on_will_start",
        "myaction_on_will_start_after",
    ]);
});

test("Call lazy session info after webclient init with action and service", async () => {
    patchWithCleanup(WebClient.prototype, {
        setup() {
            super.setup();
            onMounted(() => expect.step("web_client_mounted"));
        },
    });
    onRpc("lazy_session_info", () => {
        expect.step("load_session_info");
        return { a: "a", b: "b" };
    });
    class FakeAPlugin extends Plugin {
        lazySession = usePlugin(LazySessionPlugin);
        setup() {
            expect.step("service_before");
            this.lazySession.getValue("a", (value) => {
                expect(value).toBe("a");
                expect.step("session_after_lazy");
            });
            expect.step("service_after");
        }
    }
    services.add(FakeAPlugin);
    after(() => services.delete(FakeAPlugin));
    const actionRegistry = registry.category("actions");
    class TestClientAction extends Component {
        static template = xml`<div/>`;
        props = useProps();
        setup() {
            expect.step("myaction_before");
            this.lazySession = usePlugin(LazySessionPlugin);
            onWillStart(() => {
                expect.step("myaction_on_will_start");
                this.lazySession.getValue("b", (value) => {
                    expect(value).toEqual("b");
                    expect.step("myaction_on_will_start_after");
                });
            });
        }
    }
    actionRegistry.add("__test__client__action__", TestClientAction);

    await mountWithCleanup(WebClient);
    await animationFrame();
    await getService("action").doAction({
        tag: "__test__client__action__",
        type: "ir.actions.client",
    });
    await animationFrame();
    expect.verifySteps([
        "service_before",
        "service_after",
        "web_client_mounted",
        "load_session_info", // <= only do it once after webclient is mounted
        "session_after_lazy",
        "myaction_before",
        "myaction_on_will_start",
        "myaction_on_will_start_after",
    ]);
});
