import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { getActiveHotkey, hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { useActiveElement } from "@web/core/ui/ui_service";

import { destroy, expect, getFixture, onError, test } from "@odoo/hoot";

import { keyDown, keyUp, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent } from "@odoo/hoot-mock";
import {
    contains,
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { Component, useRef, useState, xml } from "@odoo/owl";
import { isIterable } from "@web/core/utils/arrays";
import { Deferred } from "@web/core/utils/concurrency";

/**
 * Performs a keyboard event sequence on the active element.
 *
 * The event sequence is as follow:
 *  - `keydown`
 *  - `keyup`
 * Setting addOverlayModParts to true ensures alt is pressed
 * before the given key
 * @param {string | Iterable<string>} key
 * @param {boolean} [addOverlayModParts]
 * @param {KeyboardEventInit} [options]
 */
const triggerHotkey = (key, addOverlayModParts, options) => {
    const keys = isIterable(key) ? [...key] : [key];
    if (addOverlayModParts) {
        keys.unshift("alt");
    }
    press(keys, options);
    return animationFrame();
};

const getOverlays = () => queryAllTexts(".o_web_hotkey_overlay");

test("register / unregister", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");

    const key = "q";
    await triggerHotkey(key);

    const removeHotkey = hotkey.add(key, () => expect.step(key));
    await animationFrame();

    await triggerHotkey(key);

    removeHotkey();
    await triggerHotkey(key);

    expect([key]).toVerifySteps();
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
    await triggerHotkey(key);
    expect([key]).toVerifySteps();
    removeHotkey();

    removeHotkey = hotkey.add(
        key,
        () => {
            throw new Error("error");
        },
        { global: true }
    );
    await triggerHotkey(key);
    expect(["error"]).toVerifySteps();

    // Trigger an event that doesn't honor KeyboardEvent API: that's the point
    // in particular, it has no `key`
    await triggerHotkey("");
    expect([]).toVerifySteps();
});

test("[accesskey] attrs replaced by [data-hotkey]", async () => {
    await mountWithCleanup(/* xml */ `
        <div class="foo" accessKey="a">
            foo
        </div>
    `);
    queryOne(".foo").addEventListener("click", () => expect.step("click"));

    // div must only have [accesskey] attribute
    expect(".foo").toHaveCount(1);
    expect(".foo[accesskey]").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(0);

    // press any hotkey, i.e. the left arrow
    await triggerHotkey("arrowleft");

    // div should now only have [data-hotkey] attribute
    expect(".foo").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(1);
    expect(".foo[accesskey]").toHaveCount(0);

    // try to press the related hotkey, just to make sure it works
    expect([]).toVerifySteps();
    await triggerHotkey("a", true);
    expect(["click"]).toVerifySteps();
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
    await triggerHotkey("arrowleft");

    // div should now only have [data-hotkey] attribute
    expect("main div").toHaveCount(1);
    expect("main div[data-hotkey]").toHaveCount(1);
    expect("main div[accesskey]").toHaveCount(0);

    // try to press the related hotkey, it should not work as the ui active element is different
    expect(getService("ui").getActiveElementOf(queryOne("main div"))).not.toBe(
        getService("ui").activeElement
    );
    expect([]).toVerifySteps();
    await triggerHotkey("a", true);
    expect([]).toVerifySteps();

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

    expect([]).toVerifySteps();
    await triggerHotkey("a", true);
    expect(["click"]).toVerifySteps();
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

    const key = "b";
    await triggerHotkey(key, true);
    expect([]).toVerifySteps();

    const comp = await mountWithCleanup(MyComponent);

    await triggerHotkey(key, true);
    expect(["click"]).toVerifySteps();

    destroy(comp);

    await triggerHotkey(key, true);
    expect([]).toVerifySteps();
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

    const key = "b";
    await triggerHotkey(key, true);
    expect([]).toVerifySteps();

    await mountWithCleanup(MyComponent);

    await triggerHotkey(key, true);
    expect(["click"]).toVerifySteps();

    queryOne(".myButton").disabled = true;
    await triggerHotkey(key, true);
    expect([]).toVerifySteps({ message: "shouldn't trigger the hotkey of an invisible button" });
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

    await triggerHotkey(key);

    const comp = await mountWithCleanup(TestComponent);

    await triggerHotkey(key);

    destroy(comp);

    await triggerHotkey(key);

    expect([key]).toVerifySteps();
});

test("non-MacOS usability", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    const key = "q";

    // On non-MacOS, ALT is NOT replaced by CONTROL key
    let removeHotkey = hotkey.add(`alt+${key}`, () => expect.step(`alt+${key}`));
    await animationFrame();
    await triggerHotkey(key, true);
    expect([`alt+${key}`]).toVerifySteps();

    await triggerHotkey(["ctrl", key]);
    expect([]).toVerifySteps();

    removeHotkey();

    // On non-MacOS, CONTROL is NOT replaced by COMMAND key (= metaKey)
    removeHotkey = hotkey.add(`control+${key}`, () => expect.step(`control+${key}`));
    await animationFrame();

    await triggerHotkey(["ctrl", key]);
    expect([`control+${key}`]).toVerifySteps();

    await triggerHotkey(["win", key]);
    expect([]).toVerifySteps();

    removeHotkey();
});

test("the overlay of hotkeys is correctly displayed", async () => {
    const displayHotkeysOverlay = () => {
        keyDown("alt");
    };

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

    displayHotkeysOverlay();
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });

    // apply an existent hotkey
    await triggerHotkey(["alt", "b"]);
    expect(["click b"]).toVerifySteps();
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });

    displayHotkeysOverlay();
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });

    // apply a non-existent hotkey
    await triggerHotkey(["alt", "x"]);
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });
    expect([]).toVerifySteps();
});

test("the overlay of hotkeys is correctly displayed on MacOs", async () => {
    mockUserAgent("mac");

    const displayHotkeysOverlay = () => {
        keyDown("ctrl");
    };

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

    displayHotkeysOverlay();
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });

    // apply an existent hotkey
    await triggerHotkey(["alt", "b"]);
    expect(["click b"]).toVerifySteps();
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });

    displayHotkeysOverlay();
    expect(getOverlays()).toEqual(["B", "C"], { message: "should display the overlay" });

    // apply a non-existent hotkey
    await triggerHotkey(["alt", "x"]);
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });
    expect([]).toVerifySteps();
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
    await animationFrame();
    expect(".o_web_hotkey_overlay").toHaveCount(1);

    // Hide overlays
    keyUp("alt");
    await animationFrame();
    expect(".o_web_hotkey_overlay").toHaveCount(0);

    // Display overlays
    keyDown("alt");
    await animationFrame();
    expect(".o_web_hotkey_overlay").toHaveCount(1);

    // Hide overlays
    keyUp("alt");
    await animationFrame();
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

    await triggerHotkey(["alt", "q"]);
    expect([]).toVerifySteps();

    await triggerHotkey(["ctrl", "q"]);
    expect([`alt+${key}`]).toVerifySteps();

    removeHotkey();

    // On MacOS, CONTROL is replaced by COMMAND key (= metaKey)
    removeHotkey = hotkey.add(`control+${key}`, () => expect.step(`control+${key}`));
    await animationFrame();

    await triggerHotkey(["ctrl", "q"]);
    expect([]).toVerifySteps();

    await triggerHotkey(["win", "q"]);
    expect([`control+${key}`]).toVerifySteps();

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

    await triggerHotkey(key, true);
    expect([key]).toVerifySteps();

    await triggerHotkey(key);
    expect([]).toVerifySteps();
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

    // Dispatch the three keys without repeat:
    triggerHotkey(allowRepeatKey);
    triggerHotkey(disallowRepeatKey);
    await triggerHotkey(defaultBehaviourKey);

    expect([allowRepeatKey, disallowRepeatKey, defaultBehaviourKey]).toVerifySteps();

    // Dispatch the three keys with repeat:
    triggerHotkey(allowRepeatKey, false, { repeat: true });
    triggerHotkey(disallowRepeatKey, false, { repeat: true });
    await triggerHotkey(defaultBehaviourKey, false, { repeat: true });

    expect([allowRepeatKey]).toVerifySteps();
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

    await triggerHotkey(key, true);
    expect([key]).toVerifySteps();

    await triggerHotkey(key, true, { repeat: true });
    expect([]).toVerifySteps();
});

test("hotkeys evil 👹", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");

    expect(() => hotkey.add()).toThrow(/must specify an hotkey/);
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
    triggerHotkey("a");
    triggerHotkey("b");
    await triggerHotkey("c", true);

    expect(["callback:a", "callback:b", "click"]).toVerifySteps();
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
    triggerHotkey("a");
    triggerHotkey("b");
    await triggerHotkey("c", true);
    expect(["comp1:a", "comp1:b", "comp1:c:button"]).toVerifySteps({
        message: "the callbacks of comp1 are called",
    });

    await triggerHotkey("z", true);
    expect(["comp1:z"]).toVerifySteps({
        message:
            "calls only the callback from the useHotkey registration and the button is not clicked",
    });

    await mountWithCleanup(getComp("comp2"));
    triggerHotkey("a");
    await triggerHotkey("b");
    expect(["comp2:a", "comp2:b"]).toVerifySteps({
        message: "calls only the callbacks from last useHotkey registrations",
    });

    await triggerHotkey("c", true);
    expect(["comp1:c:button"]).toVerifySteps({
        message:
            "calls only the callback of the first encountered button with proper [data-hotkey]",
    });

    await triggerHotkey("z", true);
    expect(["comp2:z"]).toVerifySteps({
        message:
            "calls only the callbacks from last useHotkey registrations and no button is clicked",
    });
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
    triggerHotkey("a");
    await triggerHotkey("b", true);

    const comp2 = await mountWithCleanup(MyComponent2);
    triggerHotkey("a");
    await triggerHotkey("b", true);

    destroy(comp2);
    triggerHotkey("a");
    await triggerHotkey("b", true);

    expect([
        "MyComponent1 subscription",
        "MyComponent1 [data-hotkey]",
        "MyComponent2 subscription",
        "MyComponent2 [data-hotkey]",
        "MyComponent1 subscription",
        "MyComponent1 [data-hotkey]",
    ]).toVerifySteps();
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
    await triggerHotkey(["alt", "shift", key]);

    expect(["click"]).toVerifySteps();

    await triggerHotkey(["alt", key]);

    expect([]).toVerifySteps();
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
    await triggerHotkey(["ctrl", "shift", key]);

    expect(["click"]).toVerifySteps();

    await triggerHotkey(["alt", key]);

    expect([]).toVerifySteps();
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

    expect([]).toVerifySteps();
    await triggerHotkey("ArrowLeft");
    expect(["called"]).toVerifySteps();

    await contains(".foo").focus();
    await triggerHotkey("ArrowLeft");
    expect([]).toVerifySteps({
        message: "the callback is not getting called when it is triggered from an editable",
    });
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

    expect([]).toVerifySteps();
    await triggerHotkey("ArrowLeft");
    expect(["called"]).toVerifySteps();

    await contains(".foo").focus();
    await triggerHotkey("ArrowLeft");
    expect(["called"]).toVerifySteps({
        message: "the callback still gets called even if triggered from an editable",
    });
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

    expect([]).toVerifySteps();
    await triggerHotkey("ArrowLeft");
    expect(["called"]).toVerifySteps();

    await contains(".foo").focus();
    await triggerHotkey("ArrowLeft");
    expect(["called"]).toVerifySteps({
        message: "the callback gets called as the foo editable allows it",
    });

    await contains(".bar").focus();
    await triggerHotkey("ArrowLeft");
    expect([]).toVerifySteps({
        message:
            "the callback does not get called as the bar editable does not explicitly allow hotkeys",
    });
});

test("ignore numpad keys", async () => {
    await makeMockEnv();
    const key = "1";
    getService("hotkey").add(`alt+${key}`, () => expect.step(key));
    await animationFrame();

    await triggerHotkey(key, true, { code: "Numpad1" });
    expect([]).toVerifySteps();

    keyDown("alt");
    await triggerHotkey("&", false, { code: "Digit1" });
    expect(["1"]).toVerifySteps();
});

test("within iframes", async () => {
    await makeMockEnv();
    getService("hotkey").add("enter", () => expect.step("called"));
    await animationFrame();

    // Dispatch directly to target to show that the hotkey service works as expected
    keyDown("Enter");
    await animationFrame();
    expect(["called"]).toVerifySteps();

    // Append an iframe to target and wait until it is fully loaded.
    const iframe = document.createElement("iframe");
    iframe.srcdoc = "<button>Hello world!</button>";
    const def = new Deferred();
    iframe.onload = def.resolve;
    getFixture().appendChild(iframe);
    await def;

    // Dispatch an hotkey from within the iframe
    await contains("iframe:iframe button").focus();
    keyDown("Enter");
    await animationFrame();
    expect([]).toVerifySteps();

    // Register the iframe to the hotkey service
    getService("hotkey").registerIframe(iframe);
    keyDown("Enter");
    await animationFrame();
    expect(["called"]).toVerifySteps();
});

test("callback: received context", async () => {
    expect.assertions(2);
    class A extends Component {
        static template = xml`<button class="a">a</button>`;
        static props = ["*"];
        setup() {
            useHotkey("a", (context) => {
                expect(context).toEqual({
                    area: undefined,
                    target: document.activeElement,
                });
            });
        }
    }
    const fixture = getFixture();
    class B extends Component {
        static template = xml`<button class="b">b</button>`;
        static props = ["*"];
        setup() {
            useHotkey(
                "b",
                (context) => {
                    expect(context).toEqual({
                        area: fixture,
                        target: fixture,
                    });
                },
                { area: () => fixture }
            );
        }
    }

    await mountWithCleanup(A);
    await mountWithCleanup(B);
    await contains(".a").focus();
    await triggerHotkey("A");
    await contains(".b").focus();
    await triggerHotkey("B");
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
    await triggerHotkey("Space");
    expect([]).toVerifySteps();

    await contains(".two").focus();
    await triggerHotkey("Space");
    expect(["RGNTDJÛ!"]).toVerifySteps();
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
    triggerHotkey("Space");
    await triggerHotkey("BackSpace");
    expect([]).toVerifySteps();

    // Trigger hotkeys from the 'two'
    await contains(".two").focus();
    triggerHotkey("Space");
    await triggerHotkey("BackSpace");
    expect(["RGNTDJÛ! (global)"]).toVerifySteps();
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

    await triggerHotkey("Space");
    expect([]).toVerifySteps();

    isAvailable = true;
    await triggerHotkey("Space");
    expect(["RGNTDJÛ!"]).toVerifySteps();
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
    await triggerHotkey("Space");
    expect([]).toVerifySteps();

    isAvailable = true;
    await triggerHotkey("Space");
    expect([]).toVerifySteps();

    // Trigger hotkeys from the 'two'
    await contains(".two").focus();

    isAvailable = false;
    await triggerHotkey("Space");
    expect([]).toVerifySteps();

    isAvailable = true;
    await triggerHotkey("Space");
    expect(["RGNTDJÛ!"]).toVerifySteps();
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
    await triggerHotkey("Space");
    expect(["withArea"]).toVerifySteps();
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
    await triggerHotkey(" "); // event key triggered by the browser
    expect(["space"]).toVerifySteps();
});

test("useHotkey can display an overlay over a DOM element ", async () => {
    const displayHotkeysOverlay = () => {
        keyDown("alt");
    };

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

    displayHotkeysOverlay();
    expect(getOverlays()).toEqual(["A"], { message: "should display the overlay" });

    await triggerHotkey(["alt", "a"]);
    expect(["hotkey alt+a has been triggered"]).toVerifySteps();
});
