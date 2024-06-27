import { destroy, expect, getFixture, onError, test } from "@odoo/hoot";
import { keyDown, keyUp, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent } from "@odoo/hoot-mock";
import { Component, useRef, useState, xml } from "@odoo/owl";
import {
    contains,
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { getActiveHotkey, hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { useActiveElement } from "@web/core/ui/ui_service";
import { Deferred } from "@web/core/utils/concurrency";

const getOverlays = () => queryAllTexts(".o_web_hotkey_overlay");

test("register / unregister", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");

    const key = "q";
    press(key);
    expect.verifySteps([]);

    const removeHotkey = hotkey.add(key, () => expect.step(key));
    await animationFrame();

    press(key);
    expect.verifySteps([key]);

    removeHotkey();
    press(key);
    expect.verifySteps([]);
});

test("should ignore when IME is composing", async () => {
    await makeMockEnv();
    const key = "enter";
    getService("hotkey").add(key, () => expect.step(key));
    await animationFrame();

    press([key]);
    expect.verifySteps([key]);

    press([key], { isComposing: true });
    expect.verifySteps([]);
});

test("hotkey handles wrongly formed KeyboardEvent", async () => {
    // This test's aim is to assert that Chrome's autofill bug is handled.
    // When filling a form with the autofill feature of Chrome, a keyboard event without any
    // key set on it is triggered. This seems to be a bug on Chrome's side, since the spec
    //doesn't mention that field may be unset. (https://developer.mozilla.org/en-US/docs/Web/API/KeyboardEvent/key).
    await makeMockEnv();

    const hotkey = getService("hotkey");

    const handler = (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
        expect.step("error");
    };

    onError(handler);

    const key = "q";
    let removeHotkey = hotkey.add(key, () => expect.step(key), { global: true });
    press(key);
    expect.verifySteps([key]);
    removeHotkey();

    removeHotkey = hotkey.add(
        key,
        () => {
            throw new Error("error");
        },
        { global: true }
    );

    press(key);
    expect.verifySteps(["error"]);

    // Trigger an event that doesn't honor KeyboardEvent API: that's the point
    // in particular, it has no `key`
    press("");
    expect.verifySteps([]);
});

test("[accesskey] attrs replaced by [data-hotkey]", async () => {
    await mountWithCleanup(/* xml */ `
        <div class="foo" accesskey="a">
            foo
        </div>
    `);
    queryOne(".foo").addEventListener("click", () => expect.step("click"));

    // div must only have [accesskey] attribute
    expect(".foo").toHaveCount(1);
    expect(".foo[accesskey]").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(0);

    // press any hotkey, i.e. the left arrow
    press("arrowleft");

    // div should now only have [data-hotkey] attribute
    expect(".foo").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(1);
    expect(".foo[accesskey]").toHaveCount(0);

    // try to press the related hotkey, just to make sure it works
    expect.verifySteps([]);
    press(["alt", "a"]);
    expect.verifySteps(["click"]);
});

test("[accesskey] attrs replaced by [data-hotkey], part 2", async () => {
    class UIOwnershipTakerComponent extends Component {
        static template = xml`<p class="owner" t-ref="bouh"><button>a</button></p>`;
        static props = ["*"];
        setup() {
            useActiveElement("bouh");
        }
    }
    class MyComponent extends Component {
        static components = { UIOwnershipTakerComponent };
        static template = xml`
            <main>
                <UIOwnershipTakerComponent t-if="state.foo" />
                <div t-on-click="() => { this.step('click'); }" accesskey="a">foo</div>
            </main>
        `;
        static props = ["*"];
        setup() {
            this.state = useState({ foo: true });
            this.step = expect.step.bind();
        }
    }
    const comp = await mountWithCleanup(MyComponent);

    // UIOwnershipTakerComponent should be there and it should be the ui active element
    expect("main .owner").toHaveCount(1);
    expect(queryOne("main .owner")).toBe(getService("ui").activeElement);

    // div must only have [accesskey] attribute
    expect("main div").toHaveCount(1);
    expect("main div[accesskey]").toHaveCount(1);
    expect("main div[data-hotkey]").toHaveCount(0);

    // press any hotkey, i.e. the left arrow
    press("arrowleft");

    // div should now only have [data-hotkey] attribute
    expect("main div").toHaveCount(1);
    expect("main div[data-hotkey]").toHaveCount(1);
    expect("main div[accesskey]").toHaveCount(0);

    // try to press the related hotkey, it should not work as the ui active element is different
    expect(getService("ui").getActiveElementOf(queryOne("main div"))).not.toBe(
        getService("ui").activeElement
    );
    expect.verifySteps([]);
    press(["alt", "a"]);
    expect.verifySteps([]);

    // remove the UIOwnershipTakerComponent
    comp.state.foo = false;
    await animationFrame();
    expect(getService("ui").getActiveElementOf(queryOne("main div"))).toBe(
        getService("ui").activeElement
    );

    expect("main .owner").toHaveCount(0);
    expect("main div").toHaveCount(1);
    expect("main div[data-hotkey]").toHaveCount(1);
    expect("main div[accesskey]").toHaveCount(0);

    expect.verifySteps([]);
    press(["alt", "a"]);
    expect.verifySteps(["click"]);
});

test("data-hotkey", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="onClick" data-hotkey="b">a</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }

    const strokes = ["alt", "b"];
    press(strokes);
    expect.verifySteps([]);

    const comp = await mountWithCleanup(MyComponent);

    press(strokes);
    expect.verifySteps(["click"]);

    destroy(comp);

    press(strokes);
    expect.verifySteps([]);
});

test("invisible data-hotkeys are not enabled. ", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="onClick" data-hotkey="b" class="myButton">a</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }

    const strokes = ["alt", "b"];
    press(strokes);
    expect.verifySteps([]);

    await mountWithCleanup(MyComponent);

    press(strokes);
    expect.verifySteps(["click"]);

    queryOne(".myButton").disabled = true;
    press(strokes);
    // shouldn't trigger the hotkey of an invisible button
    expect.verifySteps([]);
});

test("hook", async () => {
    const key = "q";
    class TestComponent extends Component {
        static template = xml`<div/>`;
        static props = ["*"];
        setup() {
            useHotkey(key, () => expect.step(key));
        }
    }

    press(key);
    expect.verifySteps([]);

    const comp = await mountWithCleanup(TestComponent);

    press(key);
    expect.verifySteps([key]);

    destroy(comp);

    press(key);
    expect.verifySteps([]);
});

test("non-MacOS usability", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    const key = "q";

    // On non-MacOS, ALT is NOT replaced by CONTROL key
    let removeHotkey = hotkey.add(`alt+${key}`, () => expect.step(`alt+${key}`));
    await animationFrame();
    press(["alt", key]);
    expect.verifySteps([`alt+${key}`]);

    press(["control", key]);
    expect.verifySteps([]);

    removeHotkey();

    // On non-MacOS, CONTROL is NOT replaced by COMMAND key (= metaKey)
    removeHotkey = hotkey.add(`control+${key}`, () => expect.step(`control+${key}`));
    await animationFrame();

    press(["control", key]);
    expect.verifySteps([`control+${key}`]);

    press(["command", key]);
    expect.verifySteps([]);

    removeHotkey();
});

test("the overlay of hotkeys is correctly displayed", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
            <button t-on-click="onClick" data-hotkey="b">b</button>
            <button t-on-click="onClick" data-hotkey="c">c</button>
            </div>
        `;
        static props = ["*"];
        onClick(ev) {
            expect.step(`click ${ev.target.dataset.hotkey}`);
        }
    }
    await mountWithCleanup(MyComponent);

    // apply an existent hotkey
    keyDown("alt");
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });
    press("b");
    expect.verifySteps(["click b"]);
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });

    // apply a non-existent hotkey
    keyDown("alt");
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });
    press("x");
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });
    expect.verifySteps([]);
});

test("the overlay of hotkeys is correctly displayed on MacOs", async () => {
    mockUserAgent("mac");
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="onClick" data-hotkey="b">b</button>
                <button t-on-click="onClick" data-hotkey="c">c</button>
            </div>
        `;
        static props = ["*"];
        onClick(ev) {
            expect.step(`click ${ev.target.dataset.hotkey}`);
        }
    }
    await mountWithCleanup(MyComponent);

    // apply an existent hotkey
    keyDown("ctrl");
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });
    press("b");
    expect.verifySteps(["click b"]);
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });

    // apply a non-existent hotkey
    keyDown("ctrl");
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });
    press("x");
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });
    expect.verifySteps([]);
});

test("overlays can be toggled multiple times in a row", async () => {
    class MyComponent extends Component {
        static template = xml`<button data-hotkey="a">a</button>`;
        static props = ["*"];
    }

    await mountWithCleanup(MyComponent);
    expect(".o_web_hotkey_overlay").toHaveCount(0);

    // Display overlays
    keyDown("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(1);

    // Hide overlays
    keyUp("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(0);

    // Display overlays
    keyDown("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(1);

    // Hide overlays
    keyUp("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(0);
});

test("MacOS usability", async () => {
    mockUserAgent("mac");
    await makeMockEnv();

    const hotkey = getService("hotkey");
    const key = "q";

    // On MacOS, ALT is replaced by CONTROL key
    let removeHotkey = hotkey.add(`alt+${key}`, () => expect.step(`alt+${key}`));
    await animationFrame();

    press(["alt", key]);
    expect.verifySteps([]);

    press(["ctrl", key]);
    expect.verifySteps([`alt+${key}`]);

    removeHotkey();

    // On MacOS, CONTROL is replaced by COMMAND key (= metaKey)
    removeHotkey = hotkey.add(`control+${key}`, () => expect.step(`control+${key}`));
    await animationFrame();

    press(["ctrl", key]);
    expect.verifySteps([]);

    press(["cmd", key]);
    expect.verifySteps([`control+${key}`]);

    removeHotkey();
});

test("[data-hotkey] alt is required", async () => {
    const key = "a";
    class TestComponent extends Component {
        static template = xml`<div><button t-on-click="onClick" data-hotkey="${key}">a</button></div>`;
        static props = ["*"];
        onClick() {
            expect.step(key);
        }
    }

    await mountWithCleanup(TestComponent);

    press(["alt", key]);
    expect.verifySteps([key]);

    press(key);
    expect.verifySteps([]);
});

test("registration allows repeat if specified", async () => {
    await makeMockEnv();

    const allowRepeatKey = "a";
    const disallowRepeatKey = "b";
    const defaultBehaviourKey = "c";

    getService("hotkey").add(allowRepeatKey, () => expect.step(allowRepeatKey), {
        allowRepeat: true,
    });
    getService("hotkey").add(disallowRepeatKey, () => expect.step(disallowRepeatKey), {
        allowRepeat: false,
    });
    getService("hotkey").add(defaultBehaviourKey, () => expect.step(defaultBehaviourKey));
    await animationFrame();

    keyDown(allowRepeatKey);
    keyDown(allowRepeatKey);
    await animationFrame();

    expect.verifySteps([allowRepeatKey, allowRepeatKey]);

    keyDown(disallowRepeatKey);
    keyDown(disallowRepeatKey);
    await animationFrame();

    expect.verifySteps([disallowRepeatKey]);

    keyDown(defaultBehaviourKey);
    keyDown(defaultBehaviourKey);
    await animationFrame();

    expect.verifySteps([defaultBehaviourKey]);
});

test("[data-hotkey] never allow repeat", async () => {
    const key = "a";
    class TestComponent extends Component {
        static template = xml`<div><button t-on-click="onClick" data-hotkey="${key}">a</button></div>`;
        static props = ["*"];
        onClick() {
            expect.step(key);
        }
    }

    await mountWithCleanup(TestComponent);

    keyDown(["alt", key]);
    expect.verifySteps([key]);

    keyDown([key]);
    expect.verifySteps([]);
});

test("hotkeys evil 👹", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");

    expect(() => hotkey.add()).toThrow(/must specify an hotkey/);
    expect(() => hotkey.add(null)).toThrow(/must specify an hotkey/);
    function callback() {}
    expect(() => hotkey.add(null, callback)).toThrow(/must specify an hotkey/);
    expect(() => hotkey.add("")).toThrow(/must specify an hotkey/);
    expect(() => hotkey.add("crap", callback)).toThrow(/not whitelisted/);
    expect(() => hotkey.add("ctrl+o", callback)).toThrow(/not whitelisted/);
    expect(() => hotkey.add("Control+o")).toThrow(/specify a callback/);
    expect(() => hotkey.add("Control+o+d", callback)).toThrow(/more than one single key part/);
});

test("component can register many hotkeys", async () => {
    class MyComponent extends Component {
        static template = xml`<div><button t-on-click="onClick" data-hotkey="c">c</button></div>`;
        static props = ["*"];
        setup() {
            useHotkey("a", () => expect.step("callback:a"));
            useHotkey("b", () => expect.step("callback:b"));
        }
        onClick() {
            expect.step("click");
        }
    }

    await mountWithCleanup(MyComponent);
    press("a");
    press("b");
    press(["alt", "c"]);
    expect.verifySteps(["callback:a", "callback:b", "click"]);
});

test("many components can register same hotkeys (call order matters)", async () => {
    const getComp = (name) => {
        const Comp = class extends Component {
            static template = xml`
                <div>
                    <button t-on-click="onClick" data-hotkey="c">c</button>
                    <button t-on-click="onClick" data-hotkey="z">z</button>
                </div>
            `;
            static props = ["*"];
            setup() {
                useHotkey("a", () => expect.step(`${name}:a`));
                useHotkey("b", () => expect.step(`${name}:b`));
                useHotkey("alt+z", () => expect.step(`${name}:z`));
            }
            onClick(ev) {
                expect.step(`${name}:${ev.target.dataset.hotkey}:button`);
            }
        };
        return Comp;
    };
    await mountWithCleanup(getComp("comp1"));
    press("a");
    press("b");
    press(["alt", "c"]);
    // the callbacks of comp1 are called
    expect.verifySteps(["comp1:a", "comp1:b", "comp1:c:button"]);

    press(["alt", "z"]);
    // calls only the callback from the useHotkey registration and the button is not clicked
    expect.verifySteps(["comp1:z"]);

    await mountWithCleanup(getComp("comp2"));
    press("a");
    press("b");
    // calls only the callbacks from last useHotkey registrations
    expect.verifySteps(["comp2:a", "comp2:b"]);

    press(["alt", "c"]);
    // calls only the callback of the first encountered button with proper [data-hotkey]
    expect.verifySteps(["comp1:c:button"]);

    press(["alt", "z"]);
    // calls only the callbacks from last useHotkey registrations and no button is clicked
    expect.verifySteps(["comp2:z"]);
});

test("registrations and elements belong to the correct UI owner", async () => {
    class MyComponent1 extends Component {
        static template = xml`<div><button data-hotkey="b" t-on-click="onClick">b</button></div>`;
        static props = ["*"];
        setup() {
            useHotkey("a", () => expect.step("MyComponent1 subscription"));
        }
        onClick() {
            expect.step("MyComponent1 [data-hotkey]");
        }
    }

    class MyComponent2 extends Component {
        static template = xml`<div t-ref="active"><button data-hotkey="b" t-on-click="onClick">b</button></div>`;
        static props = ["*"];
        setup() {
            useHotkey("a", () => expect.step("MyComponent2 subscription"));
            useActiveElement("active");
        }
        onClick() {
            expect.step("MyComponent2 [data-hotkey]");
        }
    }

    await mountWithCleanup(MyComponent1);
    press("a");
    press(["alt", "b"]);
    expect.verifySteps(["MyComponent1 subscription", "MyComponent1 [data-hotkey]"]);

    const comp2 = await mountWithCleanup(MyComponent2);
    press("a");
    press(["alt", "b"]);
    expect.verifySteps(["MyComponent2 subscription", "MyComponent2 [data-hotkey]"]);

    destroy(comp2);
    press("a");
    press(["alt", "b"]);
    expect.verifySteps(["MyComponent1 subscription", "MyComponent1 [data-hotkey]"]);
});

test("replace the overlayModifier for non-MacOs", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="onClick" data-hotkey="b">b</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }
    await mountWithCleanup(MyComponent);
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+shift",
    });
    const key = "b";
    press(["alt", "shift", key]);
    expect.verifySteps(["click"]);

    press(["alt", key]);
    expect.verifySteps([]);
});

test("replace the overlayModifier for MacOs", async () => {
    mockUserAgent("mac");

    class MyComponent extends Component {
        static template = xml`
            <div>
            <button t-on-click="onClick" data-hotkey="b">b</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }
    await mountWithCleanup(MyComponent);
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+shift",
    });

    const key = "b";
    press(["ctrl", "shift", key]);
    expect.verifySteps(["click"]);

    press(["ctrl", key]);
    expect.verifySteps([]);
});

test("protects editable elements", async () => {
    class Comp extends Component {
        static template = xml`<div><input class="foo"/></div>`;
        static props = ["*"];
        setup() {
            useHotkey("arrowleft", () => expect.step("called"));
        }
    }
    await mountWithCleanup(Comp);

    expect.verifySteps([]);
    press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".foo").focus();
    press("ArrowLeft");
    // the callback is not getting called when it is triggered from an editable
    expect.verifySteps([]);
});

test("protects editable elements: can bypassEditableProtection", async () => {
    class Comp extends Component {
        static template = xml`<div><input class="foo"/></div>`;
        static props = ["*"];
        setup() {
            useHotkey("arrowleft", () => expect.step("called"), { bypassEditableProtection: true });
        }
    }
    await mountWithCleanup(Comp);

    expect.verifySteps([]);
    press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".foo").focus();
    press("ArrowLeft");
    // the callback still gets called even if triggered from an editable
    expect.verifySteps(["called"]);
});

test("protects editable elements: an editable can allow hotkeys", async () => {
    class Comp extends Component {
        static template = xml`<div><input class="foo" data-allow-hotkeys="true"/><input class="bar"/></div>`;
        static props = ["*"];
        setup() {
            useHotkey("arrowleft", () => expect.step("called"));
        }
    }
    await mountWithCleanup(Comp);

    expect.verifySteps([]);
    press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".foo").focus();
    press("ArrowLeft");
    // the callback gets called as the foo editable allows it
    expect.verifySteps(["called"]);

    await contains(".bar").focus();
    press("ArrowLeft");
    // the callback does not get called as the bar editable does not explicitly allow hotkeys
    expect.verifySteps([]);
});

test("ignore numpad keys", async () => {
    await makeMockEnv();
    const key = "1";
    getService("hotkey").add(`alt+${key}`, () => expect.step(key));
    await animationFrame();

    keyDown("alt"); // for the whole test

    press(key, { code: "Numpad1" });
    expect.verifySteps([]);

    press(key, { code: "Digit1" });
    expect.verifySteps(["1"]);
});

test("within iframes", async () => {
    await makeMockEnv();
    getService("hotkey").add("enter", () => expect.step("called"));
    await animationFrame();

    // Dispatch directly to target to show that the hotkey service works as expected
    press("Enter");
    expect.verifySteps(["called"]);

    // Append an iframe to target and wait until it is fully loaded.
    const iframe = document.createElement("iframe");
    iframe.srcdoc = "<button>Hello world!</button>";
    const def = new Deferred();
    iframe.onload = def.resolve;
    getFixture().appendChild(iframe);
    await def;

    // Dispatch an hotkey from within the iframe
    await contains("iframe:iframe button").focus();
    press("Enter");
    expect.verifySteps([]);

    // Register the iframe to the hotkey service
    getService("hotkey").registerIframe(iframe);
    press("Enter");
    expect.verifySteps(["called"]);
});

test("callback: received context", async () => {
    class A extends Component {
        static template = xml`<button class="a">a</button>`;
        static props = ["*"];
        setup() {
            useHotkey("a", expect.step);
        }
    }
    const fixture = getFixture();
    class B extends Component {
        static template = xml`<button class="b">b</button>`;
        static props = ["*"];
        setup() {
            useHotkey("b", expect.step, { area: () => fixture });
        }
    }

    await mountWithCleanup(A);
    await mountWithCleanup(B);
    await contains(".a").press("a");
    expect.verifySteps([{ area: undefined, target: document.activeElement }]);
    await contains(".b").press("b");
    expect.verifySteps([{ area: fixture, target: document.activeElement }]);
});

test("operating area can be restricted", async () => {
    expect.assertions(3);
    class A extends Component {
        static template = xml`
            <div class="one" tabindex="0">one</div>
            <div class="two" tabindex="0" t-ref="area">two</div>
        `;
        static props = ["*"];
        setup() {
            const areaRef = useRef("area");
            useHotkey(
                "space",
                ({ area }) => {
                    expect.step("RGNTDJÛ!");
                    expect(area).toBe(queryOne(".two"));
                },
                {
                    area: () => areaRef.el,
                }
            );
        }
    }
    await mountWithCleanup(A);
    await contains(".one").focus();
    press("Space");
    expect.verifySteps([]);

    await contains(".two").focus();
    press("Space");
    expect.verifySteps(["RGNTDJÛ!"]);
});

test("operating area and UI active element", async () => {
    expect.assertions(5);
    class UIOwnershipTakerComponent extends Component {
        static template = xml`<p class="owner" t-ref="bouh"><button>a</button></p>`;
        static props = ["*"];
        setup() {
            useActiveElement("bouh");
        }
    }
    class C extends Component {
        static components = { UIOwnershipTakerComponent };
        static template = xml`
            <main>
                <UIOwnershipTakerComponent t-if="state.foo" />
                <div class="one" tabindex="0">one</div>
                <div class="two" tabindex="0" t-ref="area">two</div>
            </main>
        `;
        static props = ["*"];
        setup() {
            this.state = useState({ foo: false });
            const areaRef = useRef("area");
            useHotkey(
                "space",
                ({ area }) => {
                    expect.step("RGNTDJÛ!");
                    expect(area).toBe(queryOne(".two"));
                },
                {
                    area: () => areaRef.el,
                }
            );
            useHotkey(
                "backspace",
                ({ area }) => {
                    expect.step("RGNTDJÛ! (global)");
                    expect(area).toBe(queryOne(".two"));
                },
                {
                    area: () => areaRef.el,
                    global: true,
                }
            );
        }
    }
    const comp = await mountWithCleanup(C);
    expect(getService("ui").activeElement).toBe(document);

    // Show the UIOwnershipTaker
    comp.state.foo = true;
    await animationFrame();
    expect(getService("ui").activeElement).toHaveClass("owner");

    // Trigger hotkeys from the 'one'
    await contains(".one").focus();
    press("Space");
    press("BackSpace");
    expect.verifySteps([]);

    // Trigger hotkeys from the 'two'
    await contains(".two").focus();
    press("Space");
    press("BackSpace");
    expect.verifySteps(["RGNTDJÛ! (global)"]);
});

test("validating option", async () => {
    let isAvailable = false;
    class A extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            useHotkey(
                "space",
                () => {
                    expect.step("RGNTDJÛ!");
                },
                {
                    isAvailable: () => isAvailable,
                }
            );
        }
    }
    await mountWithCleanup(A);

    press("Space");
    expect.verifySteps([]);

    isAvailable = true;
    press("Space");
    expect.verifySteps(["RGNTDJÛ!"]);
});

test("operation area with validating option", async () => {
    let isAvailable;
    class A extends Component {
        static template = xml`
            <div class="one" tabindex="0">one</div>
            <div class="two" tabindex="0" t-ref="area">two</div>
        `;
        static props = ["*"];
        setup() {
            const areaRef = useRef("area");
            useHotkey(
                "space",
                () => {
                    expect.step("RGNTDJÛ!");
                },
                { area: () => areaRef.el, isAvailable: () => isAvailable }
            );
        }
    }
    await mountWithCleanup(A);

    // Trigger hotkeys from the 'one'
    await contains(".one").focus();

    isAvailable = false;
    press("Space");
    expect.verifySteps([]);

    isAvailable = true;
    press("Space");
    expect.verifySteps([]);

    // Trigger hotkeys from the 'two'
    await contains(".two").focus();

    isAvailable = false;
    press("Space");
    expect.verifySteps([]);

    isAvailable = true;
    press("Space");
    expect.verifySteps(["RGNTDJÛ!"]);
});

test("mixing hotkeys with and without operation area", async () => {
    class A extends Component {
        static template = xml`<div class="root" tabindex="0" t-ref="area">root</div>`;
        static props = ["*"];
        setup() {
            const areaRef = useRef("area");
            useHotkey("space", () => expect.step("withoutArea"));
            useHotkey("space", () => expect.step("withArea"), { area: () => areaRef.el });
        }
    }
    await mountWithCleanup(A);

    await contains(".root").focus();
    press("Space");
    expect.verifySteps(["withArea"]);
});

test("native browser space key ' ' is correctly translated to 'space' ", async () => {
    class A extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            useHotkey("space", () => expect.step("space"));
        }
    }

    expect(getActiveHotkey({ key: " " })).toBe("space");

    await mountWithCleanup(A);
    press([" "]); // event key triggered by the browser
    expect.verifySteps(["space"]);
});

test("useHotkey can display an overlay over a DOM element ", async () => {
    class A extends Component {
        static template = xml`<div><button class="target">Should be overlayed</button></div>`;
        static props = ["*"];
        setup() {
            useHotkey(
                "alt+a",
                () => {
                    expect.step("hotkey alt+a has been triggered");
                },
                {
                    withOverlay: () => queryOne(".target"),
                }
            );
        }
    }

    await mountWithCleanup(A);

    expect(getOverlays()).toEqual([], { message: "There is no overlay" });

    keyDown("alt");
    expect(getOverlays()).toEqual(["A"], { message: "should display the overlay" });

    press("a");
    expect.verifySteps(["hotkey alt+a has been triggered"]);
});
