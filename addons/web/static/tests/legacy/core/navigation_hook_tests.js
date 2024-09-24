/** @odoo-module alias=@web/../tests/core/navigation_hook_tests default=false */

import { Component, xml } from "@odoo/owl";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { getFixture, mount, patchWithCleanup, triggerHotkey } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { useNavigation } from "@web/core/navigation/navigation";
import { registry } from "@web/core/registry";
import { useAutofocus } from "@web/core/utils/hooks";

const serviceRegistry = registry.category("services");
let target;

/**
 * @param {import("@web/core/navigation/navigation").NavigationOptions} navOptions
 */
function createNavComponent(navOptions = {}, onClick = () => {}) {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <button class="outside" t-ref="outsideRef">outside target</button>
            <div class="container" t-ref="containerRef">
                <button class="o-navigable one" t-on-click="() => this.onClick(1)">target one</button>
                <div class="o-navigable two" tabindex="0" t-on-click="() => this.onClick(2)">target two</div>
                <input class="o-navigable three" t-on-click="() => this.onClick(3)"/><br/>
                <button class="no-nav-class">skipped</button><br/>
                <a class="o-navigable four" tabindex="0" t-on-click="() => this.onClick(4)">target four</a>
                <div class="o-navigable five">
                    <button t-on-click="() => this.onClick(5)">target five</button>
                </div>
            </div>
        `;

        setup() {
            useAutofocus({ refName: "outsideRef" });
            this.navigation = useNavigation("containerRef", navOptions);
        }

        onClick(id) {
            onClick(id);
        }
    }
    return Parent;
}

QUnit.module("Hooks", ({ beforeEach }) => {
    beforeEach(async () => {
        serviceRegistry.add("hotkey", hotkeyService);
        target = getFixture();
        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
            clearTimeout: () => {},
        });
    });

    QUnit.module("useNavigation");

    QUnit.test("default navigation [REQUIRE FOCUS]", async (assert) => {
        async function navigate(hotkey, expect) {
            await triggerHotkey(hotkey);
            assert.strictEqual(document.activeElement, target.querySelector(expect));
            assert.hasClass(target.querySelector(expect), "focus");
        }

        const env = await makeTestEnv();
        await mount(
            createNavComponent({}, (id) => assert.step(id.toString())),
            target,
            { env }
        );

        assert.strictEqual(document.activeElement, target.querySelector(".one"));
        await navigate("arrowdown", ".two");
        await navigate("arrowdown", ".three");
        await navigate("arrowdown", ".four");
        await navigate("arrowdown", ".five button");
        await navigate("arrowdown", ".one");

        await navigate("arrowup", ".five button");
        await navigate("arrowup", ".four");

        await navigate("end", ".five button");
        await navigate("home", ".one");

        await navigate("tab", ".two");
        await navigate("shift+tab", ".one");

        await navigate("arrowleft", ".one");
        await navigate("arrowright", ".one");
        await navigate("space", ".one");
        await navigate("escape", ".one");

        await triggerHotkey("enter");
        assert.verifySteps(["1"]);

        await navigate("arrowdown", ".two");
        await triggerHotkey("enter");
        assert.verifySteps(["2"]);
    });

    QUnit.test("hotkey override options [REQUIRE FOCUS]", async (assert) => {
        const env = await makeTestEnv();
        await mount(
            createNavComponent(
                {
                    hotkeys: {
                        arrowleft: (index, items) => {
                            assert.step(index.toString());
                            items[(index + 2) % items.length].focus();
                        },
                        escape: (index, items) => {
                            assert.step("escape");
                            items[0].focus();
                        },
                    },
                },
                (id) => assert.step(id.toString())
            ),
            target,
            { env }
        );

        assert.strictEqual(document.activeElement, target.querySelector(".one"));

        await triggerHotkey("arrowleft");
        assert.strictEqual(document.activeElement, target.querySelector(".three"));
        assert.verifySteps(["0"]);

        await triggerHotkey("escape");
        assert.strictEqual(document.activeElement, target.querySelector(".one"));
        assert.verifySteps(["escape"]);
    });

    QUnit.test("navigation with virtual focus [REQUIRE FOCUS]", async (assert) => {
        async function navigate(hotkey, expect) {
            await triggerHotkey(hotkey);
            // Focus is kept on button outside container
            assert.strictEqual(document.activeElement, target.querySelector(".outside"));
            // Virtually focused element has "focus" class
            assert.hasClass(target.querySelector(expect), "focus");
        }

        const env = await makeTestEnv();
        await mount(
            createNavComponent(
                {
                    virtualFocus: true,
                },
                (id) => assert.step(id.toString())
            ),
            target,
            { env }
        );

        assert.hasClass(target.querySelector(".one"), "focus");
        await navigate("arrowdown", ".two");
        await navigate("arrowdown", ".three");
        await navigate("arrowdown", ".four");
        await navigate("arrowdown", ".five button");
        await navigate("arrowdown", ".one");

        await navigate("arrowup", ".five button");
        await navigate("arrowup", ".four");

        await navigate("end", ".five button");
        await navigate("home", ".one");

        await navigate("tab", ".two");
        await navigate("shift+tab", ".one");

        await triggerHotkey("enter");
        assert.verifySteps(["1"]);

        await navigate("arrowdown", ".two");
        await triggerHotkey("enter");
        assert.verifySteps(["2"]);
    });

    QUnit.test("hovering an item makes it active but doesn't focus", async (assert) => {
        const env = await makeTestEnv();
        await mount(createNavComponent(), target, { env });

        await triggerHotkey("arrowdown");

        assert.strictEqual(document.activeElement, target.querySelector(".two"));
        assert.hasClass(target.querySelector(".two"), "focus");


        const event = new MouseEvent('mouseenter', {
            'view': window,
            'bubbles': true,
            'cancelable': true
        });
        document.querySelector(".three").dispatchEvent(event);

        assert.strictEqual(document.activeElement, target.querySelector(".two"));
        assert.hasClass(target.querySelector(".three"), "focus");
        assert.notStrictEqual(document.activeElement, target.querySelector(".three"));
        assert.hasClass(target.querySelector(".three"), "focus");

        await triggerHotkey("arrowdown");
        assert.strictEqual(document.activeElement, target.querySelector(".four"));
        assert.hasClass(target.querySelector(".four"), "focus");
    });
});
