import { Component, xml } from "@odoo/owl";
import { useNavigation } from "@web/core/navigation/navigation";
import { useAutofocus } from "@web/core/utils/hooks";
import { describe, expect, test } from "@odoo/hoot";
import { hover, press } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

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
                arrowleft: (index, items) => {
                    expect.step(index);
                    items[(index + 2) % items.length].focus();
                },
                escape: (index, items) => {
                    expect.step("escape");
                    items[0].focus();
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
