import { Component, onMounted, useState, xml } from "@odoo/owl";
import { ACTIVE_ELEMENT_CLASS, Navigator, useNavigation } from "@web/core/navigation/navigation";
import { useAutofocus } from "@web/core/utils/hooks";
import { describe, destroy, expect, test } from "@odoo/hoot";
import {
    hover,
    press,
    click,
    queryAllTexts,
    queryOne,
    manuallyDispatchProgrammaticEvent,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";

class BasicHookParent extends Component {
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
        this.navigation = useNavigation("containerRef", this.navOptions);
        onMounted(() => this.navigation.items[0]?.setActive());
    }

    navOptions = {};
    onClick(id) {}
}

describe.current.tags("desktop");

test("default navigation", async () => {
    async function navigate(hotkey, focused) {
        await press(hotkey);
        await animationFrame();

        expect(focused).toBeFocused();
        expect(focused).toHaveClass("focus");
    }

    class Parent extends BasicHookParent {
        onClick(id) {
            expect.step(id);
        }
    }

    await mountWithCleanup(Parent);

    expect(".one").toBeFocused();

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

    await press("enter");
    await animationFrame();
    expect.verifySteps([1]);

    await navigate("arrowdown", ".two");
    await press("enter");
    await animationFrame();
    expect.verifySteps([2]);
});

test("hotkey override options", async () => {
    class Parent extends BasicHookParent {
        navOptions = {
            hotkeys: {
                arrowleft: (navigator) => {
                    expect.step(navigator.activeItemIndex);
                    navigator.items[
                        (navigator.activeItemIndex + 2) % navigator.items.length
                    ].setActive();
                },
                escape: (navigator) => {
                    expect.step("escape");
                    navigator.items[0].setActive();
                },
            },
        };

        onClick(id) {
            expect.step(id);
        }
    }

    await mountWithCleanup(Parent);

    expect(".one").toBeFocused();

    await press("arrowleft");
    await animationFrame();
    expect(".three").toBeFocused();
    expect.verifySteps([0]);

    await press("escape");
    await animationFrame();
    expect(".one").toBeFocused();
    expect.verifySteps(["escape"]);
});

test("navigation with virtual focus", async () => {
    async function navigate(hotkey, expected) {
        await press(hotkey);
        await animationFrame();
        // Focus is kept on button outside container
        expect(".outside").toBeFocused();
        // Virtually focused element has "focus" class
        expect(expected).toHaveClass("focus");
    }

    class Parent extends BasicHookParent {
        navOptions = {
            virtualFocus: true,
            isNavigationAvailable: () => true,
        };

        onClick(id) {
            expect.step(id);
        }
    }

    await mountWithCleanup(Parent);

    expect(".one").toHaveClass("focus");
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

    await press("enter");
    await animationFrame();
    expect.verifySteps([1]);

    await navigate("arrowdown", ".two");
    await press("enter");
    await animationFrame();
    expect.verifySteps([2]);
});

test("hovering an item makes it active but doesn't focus", async () => {
    await mountWithCleanup(BasicHookParent);

    await press("arrowdown");

    expect(".two").toBeFocused();
    expect(".two").toHaveClass("focus");

    hover(".three");
    await animationFrame();

    expect(".two").toBeFocused();
    expect(".two").not.toHaveClass("focus");

    expect(".three").not.toBeFocused();
    expect(".three").toHaveClass("focus");

    press("arrowdown");
    await animationFrame();
    expect(".four").toBeFocused();
    expect(".four").toHaveClass("focus");
});

test("navigation disabled when component is destroyed", async () => {
    patchWithCleanup(Navigator.prototype, {
        update() {
            expect.step("enable");
            super.update();
        },
        _destroy() {
            expect.step("disable");
            super._destroy();
        },
    });
    const component = await mountWithCleanup(BasicHookParent);
    await expect.waitForSteps(["enable"]);
    destroy(component);
    await expect.waitForSteps(["disable"]);
});

test("insert item before current", async () => {
    class TestComp extends Component {
        static props = [];
        static template = xml`
            <div class="container" t-ref="containerRef">
                <t t-foreach="state.items" t-as="item" t-key="item">
                    <div class="o-navigable" t-attf-class="item-{{item}}" tabindex="0" t-esc="item"/>
                </t>
            </div>
        `;

        setup() {
            this.navigation = useNavigation("containerRef");
            this.state = useState({ items: [1, 2, 3] });
            onMounted(() => this.navigation.items[0].setActive());
        }
    }

    const component = await mountWithCleanup(TestComp);
    await press("arrowup");
    expect(queryAllTexts(".o-navigable")).toEqual(["1", "2", "3"]);
    expect(".item-3").toBeFocused();
    expect(".item-3").toHaveClass("focus");

    component.state.items.splice(2, 0, 10);
    await animationFrame();

    expect(queryAllTexts(".o-navigable")).toEqual(["1", "2", "10", "3"]);
    expect(".item-3").toBeFocused();
    expect(".item-3").toHaveClass("focus");

    await press("arrowup");
    expect(".item-10").toBeFocused();
    expect(".item-10").toHaveClass("focus");
});

test("items are focused only on mousemove, not on mouseenter", async () => {
    await mountWithCleanup(BasicHookParent);

    expect(".one").toBeFocused();

    manuallyDispatchProgrammaticEvent(queryOne(".two"), "mouseenter");
    await animationFrame();
    // mouseenter should be ignored
    expect(".two").not.toHaveClass("focus");

    await press("arrowdown");
    await animationFrame();
    expect(".two").toHaveClass("focus");

    manuallyDispatchProgrammaticEvent(queryOne(".three"), "mousemove");
    await animationFrame();
    // mousemove should not be ignored
    expect(".three").toHaveClass("focus");
    expect(".two").not.toHaveClass("focus");

    manuallyDispatchProgrammaticEvent(queryOne(".three"), "mousemove");
    await animationFrame();
    expect(".three").toHaveClass("focus");
});

test("non-navigable dom update does NOT cause re-focus", async () => {
    // An issue could be cause when for example the ALT key is pressed
    // to show the hotkeys, which would cause a DOM update and a refocus
    // of one of the navigable item.

    class Parent extends Component {
        static props = [];
        static template = xml`
            <button class="outside" t-ref="outsideRef">outside target</button>
            <div class="container" t-ref="containerRef">
                <button class="o-navigable one" t-on-click="() => this.onClick(1)">target one</button>
                <div class="test-non-navigable" t-if="state.show">
                </div>
            </div>
        `;

        setup() {
            this.navigation = useNavigation("containerRef");
            onMounted(() => this.navigation.items[0]?.setActive());
            this.state = useState({ show: false });
        }
    }

    const component = await mountWithCleanup(Parent);
    expect(".test-non-navigable").toHaveCount(0);
    expect(".one").toBeFocused();

    await click(".outside");
    expect(".one").not.toBeFocused();

    component.state.show = true;
    await animationFrame();
    expect(".test-non-navigable").toHaveCount(1);
    expect(".one").not.toBeFocused();
});

test("mousehover only set active if navigation is availible", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <div class="container" t-ref="containerRef">
                <button class="o-navigable one">target one</button>
                <button class="o-navigable two">target two</button>
            </div>
        `;

        setup() {
            this.navigation = useNavigation("containerRef");
        }
    }

    const component = await mountWithCleanup(Parent);
    expect(".one").not.toBeFocused();
    expect(".two").not.toBeFocused();
    expect(component.navigation.activeItem).toBe(null);

    await hover(".one");
    expect(component.navigation.activeItem).toBe(null);

    await hover(".two");
    expect(component.navigation.activeItem).toBe(null);

    await click(".one");
    expect(".one").toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(".two").not.toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(component.navigation.activeItem.target).toBe(queryOne(".one"));

    await hover(".two");
    expect(".one").not.toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(".two").toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(component.navigation.activeItem.target).toBe(queryOne(".two"));
});

test("active item is unset when focusing out", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <button class="outside">outside</button>
            <div class="container" t-ref="containerRef">
                <button class="o-navigable one">target one</button>
                <button class="o-navigable two">target two</button>
            </div>
        `;

        setup() {
            this.navigation = useNavigation("containerRef");
        }
    }

    const component = await mountWithCleanup(Parent);
    await click(".one");
    expect(".one").toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(".two").not.toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(component.navigation.activeItem.target).toEqual(queryOne(".one"));

    await click(".outside");
    expect(".one").not.toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(".two").not.toHaveClass(ACTIVE_ELEMENT_CLASS);
    expect(component.navigation.activeItem).toBe(null);
});
