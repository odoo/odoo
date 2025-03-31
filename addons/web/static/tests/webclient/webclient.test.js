import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, xml } from "@odoo/owl";

import {
    contains,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";

test("can be rendered", async () => {
    await mountWithCleanup(WebClient);

    expect(`header > nav.o_main_navbar`).toHaveCount(1);
});

test("can render a main component", async () => {
    class MyComponent extends Component {
        static props = {};
        static template = xml`<span class="chocolate">MyComponent</span>`;
    }

    const env = await makeMockEnv();
    registry.category("main_components").add("mycomponent", { Component: MyComponent });

    await mountWithCleanup(WebClient, { env });

    expect(`.chocolate`).toHaveCount(1);
});

test.tags("desktop");
test("control-click <a href/> in a standalone component", async () => {
    class MyComponent extends Component {
        static props = {};
        static template = xml`<a href="#" class="MyComponent" t-on-click="onclick">Some link</a>`;

        /** @param {MouseEvent} ev */
        onclick(ev) {
            expect.step(ev.ctrlKey ? "ctrl-click" : "click");
            // Necessary in order to prevent the test browser to open in new tab on ctrl-click
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
                // Necessary in order to prevent the test browser to open in new tab on ctrl-click
                ev.preventDefault();
            }
        },
    });

    class MyComponent extends Component {
        static props = {};
        static template = xml`<a href="#" class="MyComponent" t-on-click="onclick">Some link</a>`;

        /** @param {MouseEvent} ev */
        onclick(ev) {
            expect.step(ev.ctrlKey ? "ctrl-click" : "click");
            // Necessary in order to prevent the test browser to open in new tab on ctrl-click
            ev.preventDefault();
        }
    }

    await mountWithCleanup(WebClient);

    registry.category("main_components").add("mycomponent", { Component: MyComponent });
    await animationFrame();

    expect.verifySteps([]);

    await contains(".MyComponent").click();
    await contains(".MyComponent").click({ ctrlKey: true });

    expect.verifySteps(["click"]);
});
