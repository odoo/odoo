import { describe, expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-mock";
import { queryFirst } from "@odoo/hoot-dom";
import { Component, xml } from "@odoo/owl";
import { useRef } from "@web/owl2/utils";

import {
    contains,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";
import { WebClient } from "@web/webclient/webclient";
import { useStickyNavbar } from "@web/core/utils/hooks";

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
        static template = xml`<a href="#" class="MyComponent" t-on-click="this.onclick">Some link</a>`;

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
        static template = xml`<a href="#" class="MyComponent" t-on-click="this.onclick">Some link</a>`;

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

describe("useStickyNavbar", () => {
    test.tags("mobile");
    test("navbar and control panel translate on scroll, capped at combined height", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <div class="o_web_client">
                    <div class="o_navbar" t-custom-ref="navbar" style="height: 40px;">Navbar</div>
                    <div class="o_action_manager">
                        <div class="o_view_controller o_action" style="height: 600px; overflow: auto;">
                            <div class="o_control_panel" t-custom-ref="controlPanel" style="height: 60px;">Control Panel</div>
                            <div class="o_content" style="min-height: 1000px;">Content</div>
                        </div>
                    </div>
                </div>
            `;
            setup() {
                this.navbarRef = useRef("navbar");
                this.controlPanelRef = useRef("controlPanel");
                useStickyNavbar({
                    navbarRef: this.navbarRef,
                    controlPanelRef: this.controlPanelRef,
                });
            }
        }

        await mountWithCleanup(MyComponent);
        const scrollingEl = document.querySelector(".o_view_controller");
        const navbar = queryFirst(".o_navbar");
        const controlPanel = queryFirst(".o_control_panel");
        const maxTranslate = navbar.clientHeight + controlPanel.clientHeight;

        scrollingEl.scrollTo({ top: 60 });
        await animationFrame();
        expect(navbar.style.transform).toInclude("translateY(-60px)");
        expect(controlPanel.style.transform).toInclude("translateY(-60px)");

        scrollingEl.scrollTo({ top: 300 });
        await animationFrame();
        expect(navbar.style.transform).toInclude(`translateY(-${maxTranslate}px)`);
        expect(controlPanel.style.transform).toInclude(`translateY(-${maxTranslate}px)`);

        scrollingEl.scrollTo({ top: 250 });
        await animationFrame();
        expect(navbar.style.transform).toInclude(`translateY(-${maxTranslate - 50}px)`);
        expect(controlPanel.style.transform).toInclude(`translateY(-${maxTranslate - 50}px)`);
    });

    test.tags("mobile");
    test("STICKY_NAVBAR:DOCKED resets transform and freezes scroll handling", async () => {
        class MyComponent extends Component {
            static props = ["*"];
            static template = xml`
                <div class="o_web_client">
                    <div class="o_navbar" t-custom-ref="navbar" style="height: 40px;">Navbar</div>
                    <div class="o_action_manager">
                        <div class="o_view_controller o_action" style="height: 600px; overflow: auto;">
                            <div class="o_control_panel" t-custom-ref="controlPanel" style="height: 60px;">Control Panel</div>
                            <div class="o_content" style="min-height: 1000px;">
                                <button id="toggle" t-on-click="this.toggleDocked">Toggle Docked</button>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            setup() {
                this.navbarRef = useRef("navbar");
                this.controlPanelRef = useRef("controlPanel");
                this.isDocked = false;
                useStickyNavbar({
                    navbarRef: this.navbarRef,
                    controlPanelRef: this.controlPanelRef,
                });
            }
            toggleDocked() {
                this.isDocked = !this.isDocked;
                this.env.bus.trigger("STICKY_NAVBAR:RESET_STATE", { isDocked: this.isDocked });
            }
        }

        await makeMockEnv();
        await mountWithCleanup(MyComponent);
        const scrollingEl = document.querySelector(".o_view_controller");
        const navbar = queryFirst(".o_navbar");
        const controlPanel = queryFirst(".o_control_panel");

        // Scroll down to get a transform
        scrollingEl.scrollTo({ top: 60 });
        await animationFrame();
        expect(navbar.style.transform).toInclude("translateY(-60px)");
        expect(controlPanel.style.transform).toInclude("translateY(-60px)");

        // Docking resets the transform
        await contains("#toggle").click();
        await animationFrame();
        expect(navbar.style.transform).not.toInclude("translateY");
        expect(controlPanel.style.transform).not.toInclude("translateY");

        // Further scrolling while docked has no effect
        scrollingEl.scrollTo({ top: 300 });
        await animationFrame();
        expect(navbar.style.transform).not.toInclude("translateY");
        expect(controlPanel.style.transform).not.toInclude("translateY");

        // Undocking makes the element visible again and re-enables scroll handling
        await contains("#toggle").click();
        expect(navbar.style.transform).not.toInclude("translateY");
        expect(controlPanel.style.transform).not.toInclude("translateY");
        scrollingEl.scrollTo({ top: 360 });
        await animationFrame();
        expect(navbar.style.transform).toInclude("translateY(-60px)");
        expect(controlPanel.style.transform).toInclude("translateY(-60px)");
    });
});
