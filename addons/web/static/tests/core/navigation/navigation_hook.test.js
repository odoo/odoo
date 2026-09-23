// @ts-check

import { describe, destroy, expect, test } from "@odoo/hoot";
import {
    click,
    hover,
    manuallyDispatchProgrammaticEvent,
    press,
    queryAllTexts,
    queryOne,
} from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { Component, onMounted, useState, xml } from "@odoo/owl";
import { mountWithCleanup, patchWithCleanup } from "@web/../tests/web_test_helpers";
import {
    ACTIVE_ELEMENT_CLASS,
    mergeNavigationOptions,
    Navigator,
    useNavigation,
} from "@web/core/navigation/navigation";
import { useAutofocus } from "@web/core/utils/hooks";

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

    /** @type {ReturnType<typeof useNavigation>} */
    navigation;

    setup() {
        useAutofocus({ refName: "outsideRef" });
        this.navigation = useNavigation("containerRef", this.navOptions);
        onMounted(() => this.navigation.items[0]?.setActive());
    }

    navOptions = {};
    onClick(/** @type {any} */ id) {}
}

describe.current.tags("desktop");

test("default navigation", async () => {
    async function navigate(/** @type {any} */ hotkey, /** @type {any} */ focused) {
        await press(hotkey);
        await animationFrame();

        expect(focused).toBeFocused();
        expect(focused).toHaveClass("focus");
    }

    class Parent extends BasicHookParent {
        onClick(/** @type {any} */ id) {
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
                arrowleft: (/** @type {any} */ navigator) => {
                    expect.step(navigator.activeItemIndex);
                    navigator.items[
                        (navigator.activeItemIndex + 2) % navigator.items.length
                    ].setActive();
                },
                escape: (/** @type {any} */ navigator) => {
                    expect.step("escape");
                    navigator.items[0].setActive();
                },
            },
        };

        onClick(/** @type {any} */ id) {
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
    async function navigate(/** @type {any} */ hotkey, /** @type {any} */ expected) {
        await press(hotkey);
        await animationFrame();
        expect(".outside").toBeFocused();
        expect(expected).toHaveClass("focus");
    }

    class Parent extends BasicHookParent {
        navOptions = {
            virtualFocus: true,
            isNavigationAvailable: () => true,
        };

        onClick(/** @type {any} */ id) {
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

test("virtualFocus navigates by keyboard without a custom availability predicate", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <button class="outside">outside</button>
            <div class="container" t-ref="containerRef">
                <input class="search" t-ref="autofocus"/>
                <button class="o-navigable one" t-on-click="() => this.onClick(1)">one</button>
                <button class="o-navigable two" t-on-click="() => this.onClick(2)">two</button>
            </div>`;
        /** @type {ReturnType<typeof useNavigation>} */
        navigation;

        setup() {
            useAutofocus();
            this.navigation = useNavigation("containerRef", { virtualFocus: true });
        }
        onClick(/** @type {any} */ id) {
            expect.step(id);
        }
    }
    await mountWithCleanup(Parent);
    expect(".search").toBeFocused();

    await press("arrowdown");
    await animationFrame();
    expect(".one").toHaveClass("focus");
    expect(".search").toBeFocused();

    await press("arrowdown");
    await animationFrame();
    expect(".two").toHaveClass("focus");
    expect(".search").toBeFocused();

    await press("enter");
    await animationFrame();
    expect.verifySteps([2]);

    await click(".outside");
    await press("arrowdown");
    await animationFrame();
    expect(".two").not.toHaveClass("focus");
    expect(".one").not.toHaveClass("focus");
});

test("wrap: false clears past either end and re-enters from the opposite one", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <div class="container" t-ref="containerRef">
                <input class="search" t-ref="autofocus"/>
                <button class="o-navigable one">one</button>
                <button class="o-navigable two">two</button>
                <button class="o-navigable three">three</button>
            </div>`;
        /** @type {ReturnType<typeof useNavigation>} */
        navigation;

        setup() {
            useAutofocus();
            this.navigation = useNavigation("containerRef", {
                virtualFocus: true,
                wrap: false,
            });
        }
    }
    const component = await mountWithCleanup(Parent);
    expect(".search").toBeFocused();
    expect(component.navigation.activeItem).toBe(null);

    await press("arrowdown");
    expect(".one").toHaveClass("focus");

    await press("arrowdown");
    await press("arrowdown");
    expect(".three").toHaveClass("focus");

    await press("arrowdown");
    expect(component.navigation.activeItem).toBe(null);
    expect(".one").not.toHaveClass("focus");
    expect(".three").not.toHaveClass("focus");

    await press("arrowdown");
    expect(".one").toHaveClass("focus");

    await press("arrowup");
    expect(component.navigation.activeItem).toBe(null);
    await press("arrowup");
    expect(".three").toHaveClass("focus");
});

test("activateFirst, activateLast and clearActiveItem drive the cursor directly", async () => {
    class Parent extends BasicHookParent {}
    const component = await mountWithCleanup(Parent);
    expect(".one").toBeFocused();

    component.navigation.activateLast();
    await animationFrame();
    expect(".five button").toHaveClass("focus");

    component.navigation.activateFirst();
    await animationFrame();
    expect(".one").toHaveClass("focus");

    component.navigation.clearActiveItem();
    await animationFrame();
    expect(component.navigation.activeItem).toBe(null);
    expect(".one").not.toHaveClass("focus");
    expect(".one").toBeFocused();
});

test("activeClass replaces the default focus class", async () => {
    class Parent extends BasicHookParent {
        navOptions = { activeClass: "o-my-active" };
    }
    await mountWithCleanup(Parent);
    expect(".one").toBeFocused();
    expect(".one").toHaveClass("o-my-active");
    expect(".one").not.toHaveClass("focus");

    await press("arrowdown");
    await animationFrame();
    expect(".two").toHaveClass("o-my-active");
    expect(".two").not.toHaveClass("focus");
    expect(".one").not.toHaveClass("o-my-active");
});

test("armed mouse activation ignores enter/leave the pointer did not cause", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <div class="container" t-ref="containerRef">
                <div class="row r1"><button class="o-navigable one">one</button></div>
                <div class="row r2"><button class="o-navigable two">two</button></div>
                <div class="row r3"><button class="o-navigable three">three</button></div>
            </div>`;
        /** @type {ReturnType<typeof useNavigation>} */
        navigation;

        setup() {
            this.navigation = useNavigation("containerRef", {
                mouseActivation: "armed",
                getHoverTarget: (el) => /** @type {HTMLElement} */ (el.closest(".row")),
            });
        }
    }
    const component = await mountWithCleanup(Parent);

    await click(".one");
    expect(".one").toHaveClass("focus");
    expect(component.navigation.isMouseArmed).toBe(true);

    await hover(".r2");
    expect(".two").toHaveClass("focus");
    expect(".one").not.toHaveClass("focus");

    await press("arrowdown");
    expect(".three").toHaveClass("focus");
    expect(component.navigation.isMouseArmed).toBe(false);

    manuallyDispatchProgrammaticEvent(queryOne(".r3"), "mouseleave");
    await animationFrame();
    expect(".three").toHaveClass("focus");
    manuallyDispatchProgrammaticEvent(queryOne(".r1"), "mouseenter");
    await animationFrame();
    expect(".three").toHaveClass("focus");
    expect(".one").not.toHaveClass("focus");

    await hover(".r1");
    expect(".one").toHaveClass("focus");
    expect(".three").not.toHaveClass("focus");
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
                <t t-foreach="this.state.items" t-as="item" t-key="item">
                    <div class="o-navigable" t-attf-class="item-{{item}}" tabindex="0" t-out="item"/>
                </t>
            </div>
        `;

        /** @type {ReturnType<typeof useNavigation>} */
        navigation;

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
    expect(".two").not.toHaveClass("focus");

    await press("arrowdown");
    await animationFrame();
    expect(".two").toHaveClass("focus");

    manuallyDispatchProgrammaticEvent(queryOne(".three"), "mousemove");
    await animationFrame();
    expect(".three").toHaveClass("focus");
    expect(".two").not.toHaveClass("focus");

    manuallyDispatchProgrammaticEvent(queryOne(".three"), "mousemove");
    await animationFrame();
    expect(".three").toHaveClass("focus");
});

test("non-navigable dom update does NOT cause re-focus", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <button class="outside" t-ref="outsideRef">outside target</button>
            <div class="container" t-ref="containerRef">
                <button class="o-navigable one" t-on-click="() => this.onClick(1)">target one</button>
                <div class="test-non-navigable" t-if="this.state.show">
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

test("set focused element as active item", async () => {
    class Parent extends Component {
        static props = [];
        static template = xml`
            <div class="container" t-ref="containerRef">
                <input class="o-navigable one" id="input" t-ref="autofocus"/>
                <button class="o-navigable two">target two</button>
                <button class="o-navigable three">target three</button>
            </div>
        `;

        setup() {
            this.inputRef = useAutofocus();
            this.navigation = useNavigation("containerRef");
        }
    }

    const component = await mountWithCleanup(Parent);
    expect(component.inputRef.el).toBeFocused();
    expect(component.navigation.activeItem).not.toBeEmpty();
    expect(component.navigation.activeItem.el).toBe(component.inputRef.el);
});

describe("options declared as accessors stay live", () => {
    test("mergeNavigationOptions keeps a getter live across the merge", () => {
        let searchable = true;
        const source = {
            get virtualFocus() {
                return searchable;
            },
        };
        const merged = mergeNavigationOptions({ virtualFocus: false }, source);
        expect(merged.virtualFocus).toBe(true);
        searchable = false;
        expect(merged.virtualFocus).toBe(false);
    });

    test("a later plain value beats an earlier getter", () => {
        const withGetter = {
            get virtualFocus() {
                return true;
            },
        };
        const merged = mergeNavigationOptions(withGetter, { virtualFocus: false });
        expect(merged.virtualFocus).toBe(false);
    });

    test("a later getter beats an earlier one", () => {
        const first = {
            get virtualFocus() {
                return true;
            },
        };
        const second = {
            get virtualFocus() {
                return false;
            },
        };
        expect(mergeNavigationOptions(first, second).virtualFocus).toBe(false);
    });

    test("undefined sources are skipped and nothing is mutated", () => {
        const source = { shouldFocusFirstItem: true };
        const merged = mergeNavigationOptions(undefined, source, undefined);
        expect(merged.shouldFocusFirstItem).toBe(true);
        expect(merged).not.toBe(source);
        merged.shouldFocusFirstItem = false;
        expect(source.shouldFocusFirstItem).toBe(true);
    });

    test("the navigator reads a getter option at use time, not at setup", async () => {
        const state = { virtualFocus: true };
        class Parent extends Component {
            static props = [];
            static template = xml`
                <div class="container" t-ref="containerRef">
                    <button class="o-navigable one">one</button>
                    <button class="o-navigable two">two</button>
                </div>`;
            setup() {
                this.navigation = useNavigation("containerRef", {
                    get virtualFocus() {
                        return state.virtualFocus;
                    },
                });
            }
        }
        const component = await mountWithCleanup(Parent);
        const options = /** @type {any} */ (component.navigation)._options;
        expect(options.virtualFocus).toBe(true);
        state.virtualFocus = false;
        expect(options.virtualFocus).toBe(false);
    });
});
