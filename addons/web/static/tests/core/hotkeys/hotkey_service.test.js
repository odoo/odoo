// @ts-check

import { destroy, expect, getFixture, onError, test } from "@odoo/hoot";
import { keyDown, keyUp, press, queryAllTexts, queryOne } from "@odoo/hoot-dom";
import { animationFrame, mockUserAgent, tick } from "@odoo/hoot-mock";
import { Component, useRef, useState, xml } from "@odoo/owl";
import {
    contains,
    getService,
    makeMockEnv,
    mountWithCleanup,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { getActiveHotkey } from "@web/core/browser/hotkeys";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { HotkeyService, hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { Deferred } from "@web/core/utils/concurrency";
import { useActiveElement } from "@web/ui/ui_service";

const getOverlays = () => queryAllTexts(".o_web_hotkey_overlay");

test("register / unregister", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");

    const key = "q";
    await press(key);
    expect.verifySteps([]);

    const removeHotkey = hotkey.add(key, () => expect.step(key));
    await animationFrame();

    await press(key);
    expect.verifySteps([key]);

    removeHotkey();
    await press(key);
    expect.verifySteps([]);
});

test("should ignore when IME is composing", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    const key = "enter";
    hotkey.add(key, () => expect.step(key));
    await animationFrame();
    await press(key);
    expect.verifySteps([key]);
    await press(key, { isComposing: true });
    expect.verifySteps([]);
});

test("hotkey handles wrongly formed KeyboardEvent", async () => {
    await makeMockEnv();

    const hotkey = getService("hotkey");

    const handler = (ev) => {
        ev.stopPropagation();
        ev.preventDefault();
        expect.step("error");
    };

    onError(handler);

    const key = "q";
    const removeHotkey = hotkey.add(key, () => expect.step(key), { global: true });
    await press(key);
    expect.verifySteps([key]);
    removeHotkey();

    hotkey.add(
        key,
        () => {
            throw new Error("error");
        },
        { global: true },
    );

    await press(key);
    expect.verifySteps(["error"]);

    await press("");
    expect.verifySteps([]);
});

test("[accesskey] attrs replaced by [data-hotkey]", async () => {
    await mountWithCleanup(`
        <div class="foo" accesskey="a">
            foo
        </div>
    `);
    queryOne(".foo").addEventListener("click", () => expect.step("click"));

    expect(".foo").toHaveCount(1);
    expect(".foo[accesskey]").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(0);

    await press("arrowleft");
    expect(".foo[accesskey]").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(0);

    await press(["alt", "arrowleft"]);

    expect(".foo").toHaveCount(1);
    expect(".foo[data-hotkey]").toHaveCount(1);
    expect(".foo[accesskey]").toHaveCount(0);

    expect.verifySteps([]);
    await press(["alt", "a"]);
    await tick();
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
                <UIOwnershipTakerComponent t-if="this.state.foo" />
                <div t-on-click="() => { this.step('click'); }" accesskey="a">foo</div>
            </main>
        `;
        static props = ["*"];
        setup() {
            this.state = useState({ foo: true });
            this.step = expect.step;
        }
    }
    const comp = await mountWithCleanup(MyComponent);

    expect("main .owner").toHaveCount(1);
    expect(queryOne("main .owner")).toBe(
        /** @type {any} */ (getService("ui").activeElement),
    );

    expect("main div").toHaveCount(1);
    expect("main div[accesskey]").toHaveCount(1);
    expect("main div[data-hotkey]").toHaveCount(0);

    await press(["alt", "arrowleft"]);
    expect("main div").toHaveCount(1);
    expect("main div[data-hotkey]").toHaveCount(0);
    expect("main div[accesskey]").toHaveCount(1);

    expect(getService("ui").getActiveElementOf(queryOne("main div"))).not.toBe(
        getService("ui").activeElement,
    );
    expect.verifySteps([]);
    await press(["alt", "a"]);
    await tick();
    expect.verifySteps([]);
    expect("main div[accesskey]").toHaveCount(1);

    comp.state.foo = false;
    await animationFrame();
    expect(getService("ui").getActiveElementOf(queryOne("main div"))).toBe(
        getService("ui").activeElement,
    );

    expect("main .owner").toHaveCount(0);
    expect("main div").toHaveCount(1);

    expect.verifySteps([]);
    await press(["alt", "a"]);
    await tick();
    expect("main div[data-hotkey]").toHaveCount(1);
    expect("main div[accesskey]").toHaveCount(0);
    expect.verifySteps(["click"]);
});

test("data-hotkey", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="this.onClick" data-hotkey="b">a</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }

    const strokes = ["alt", "b"];
    await press(strokes);
    expect.verifySteps([]);

    const comp = await mountWithCleanup(MyComponent);

    await press(strokes);
    await tick();
    expect.verifySteps(["click"]);

    destroy(comp);

    await press(strokes);
    expect.verifySteps([]);
});

test("invisible data-hotkeys are not enabled. ", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="this.onClick" data-hotkey="b" class="myButton">a</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }

    const strokes = ["alt", "b"];
    await press(strokes);
    expect.verifySteps([]);

    await mountWithCleanup(MyComponent);

    await press(strokes);
    await tick();
    expect.verifySteps(["click"]);

    /** @type {HTMLButtonElement} */ (queryOne(".myButton")).disabled = true;
    await press(strokes);
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

    await press(key);
    expect.verifySteps([]);

    const comp = await mountWithCleanup(TestComponent);

    await press(key);
    expect.verifySteps([key]);

    destroy(comp);

    await press(key);
    expect.verifySteps([]);
});

test("non-MacOS usability", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    const key = "q";

    let removeHotkey = hotkey.add(`alt+${key}`, () => expect.step(`alt+${key}`));
    await animationFrame();
    await press(["alt", key]);
    expect.verifySteps([`alt+${key}`]);

    await press(["control", key]);
    expect.verifySteps([]);

    removeHotkey();

    removeHotkey = hotkey.add(`control+${key}`, () => expect.step(`control+${key}`));
    await animationFrame();

    await press(["control", key]);
    expect.verifySteps([`control+${key}`]);

    await press(["command", key]);
    expect.verifySteps([]);

    removeHotkey();
});

test("the overlay of hotkeys is correctly displayed", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
            <button t-on-click="this.onClick" data-hotkey="b">b</button>
            <button t-on-click="this.onClick" data-hotkey="c">c</button>
            </div>
        `;
        static props = ["*"];
        onClick(ev) {
            expect.step(`click ${ev.target.dataset.hotkey}`);
        }
    }
    await mountWithCleanup(MyComponent);

    await keyDown("alt");
    expect(getOverlays()).toEqual(["B", "C"], {
        message: "should display the overlay",
    });
    await press("b");
    await tick();
    expect.verifySteps(["click b"]);
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });

    await keyDown("alt");
    expect(getOverlays()).toEqual(["B", "C"], {
        message: "should display the overlay",
    });
    await press("x");
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });
    expect.verifySteps([]);
});

test("the overlay of hotkeys is correctly displayed on MacOs", async () => {
    mockUserAgent("mac");
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="this.onClick" data-hotkey="b">b</button>
                <button t-on-click="this.onClick" data-hotkey="c">c</button>
            </div>
        `;
        static props = ["*"];
        onClick(ev) {
            expect.step(`click ${ev.target.dataset.hotkey}`);
        }
    }
    await mountWithCleanup(MyComponent);

    await keyDown("ctrl");
    expect(getOverlays()).toEqual(["B", "C"], {
        message: "should display the overlay",
    });
    await press("b");
    await tick();
    expect.verifySteps(["click b"]);
    expect(getOverlays()).toEqual([], { message: "shouldn't display the overlay" });

    await keyDown("ctrl");
    expect(getOverlays()).toEqual(["B", "C"], {
        message: "should display the overlay",
    });
    await press("x");
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

    await keyDown("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(1);

    await keyUp("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(0);

    await keyDown("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(1);

    await keyUp("alt");
    expect(".o_web_hotkey_overlay").toHaveCount(0);
});

test("MacOS usability", async () => {
    mockUserAgent("mac");
    await makeMockEnv();

    const hotkey = getService("hotkey");
    const key = "q";

    let removeHotkey = hotkey.add(`alt+${key}`, () => expect.step(`alt+${key}`));
    await animationFrame();

    await press(["alt", key]);
    expect.verifySteps([]);

    await press(["ctrl", key]);
    expect.verifySteps([`alt+${key}`]);

    removeHotkey();

    removeHotkey = hotkey.add(`control+${key}`, () => expect.step(`control+${key}`));
    await animationFrame();

    await press(["ctrl", key]);
    expect.verifySteps([]);

    await press(["cmd", key]);
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

    await press(["alt", key]);
    await tick();
    expect.verifySteps([key]);

    await press(key);
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
    getService("hotkey").add(defaultBehaviourKey, () =>
        expect.step(defaultBehaviourKey),
    );
    await animationFrame();

    await keyDown(allowRepeatKey);
    await keyDown(allowRepeatKey);
    await animationFrame();

    expect.verifySteps([allowRepeatKey, allowRepeatKey]);

    await keyDown(disallowRepeatKey);
    await keyDown(disallowRepeatKey);
    await animationFrame();

    expect.verifySteps([disallowRepeatKey]);

    await keyDown(defaultBehaviourKey);
    await keyDown(defaultBehaviourKey);
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

    await keyDown(["alt", key]);
    await tick();
    expect.verifySteps([key]);

    await keyDown([key]);
    expect.verifySteps([]);
});

test("hotkeys evil 👹", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");

    // @ts-expect-error
    expect(() => hotkey.add()).toThrow(/must specify an hotkey/);
    // @ts-expect-error
    expect(() => hotkey.add(null)).toThrow(/must specify an hotkey/);
    function callback() {}
    expect(() => hotkey.add(null, callback)).toThrow(/must specify an hotkey/);
    // @ts-expect-error
    expect(() => hotkey.add("")).toThrow(/must specify an hotkey/);
    expect(() => hotkey.add("crap", callback)).toThrow(/not whitelisted/);
    expect(() => hotkey.add("ctrl+o", callback)).toThrow(/not whitelisted/);
    // @ts-expect-error
    expect(() => hotkey.add("Control+o")).toThrow(/specify a callback/);
    expect(() => hotkey.add("Control+o+d", callback)).toThrow(
        /more than one single key part/,
    );
});

test("component can register many hotkeys", async () => {
    class MyComponent extends Component {
        static template = xml`<div><button t-on-click="this.onClick" data-hotkey="c">c</button></div>`;
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
    await press("a");
    await press("b");
    await press(["alt", "c"]);
    await tick();
    expect.verifySteps(["callback:a", "callback:b", "click"]);
});

test("many components can register same hotkeys (call order matters)", async () => {
    const getComp = (name) => {
        const Comp = class extends Component {
            static template = xml`
                <div>
                    <button t-on-click="this.onClick" data-hotkey="c">c</button>
                    <button t-on-click="this.onClick" data-hotkey="z">z</button>
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
    await press("a");
    await press("b");
    await press(["alt", "c"]);
    await tick();
    expect.verifySteps(["comp1:a", "comp1:b", "comp1:c:button"]);

    await press(["alt", "z"]);
    expect.verifySteps(["comp1:z"]);

    await mountWithCleanup(getComp("comp2"));
    await press("a");
    await press("b");
    await tick();
    expect.verifySteps(["comp2:a", "comp2:b"]);

    await press(["alt", "c"]);
    await tick();
    expect.verifySteps(["comp1:c:button"]);

    await press(["alt", "z"]);
    expect.verifySteps(["comp2:z"]);
});

test("registrations and elements belong to the correct UI owner", async () => {
    class MyComponent1 extends Component {
        static template = xml`<div><button data-hotkey="b" t-on-click="this.onClick">b</button></div>`;
        static props = ["*"];
        setup() {
            useHotkey("a", () => expect.step("MyComponent1 subscription"));
        }
        onClick() {
            expect.step("MyComponent1 [data-hotkey]");
        }
    }

    class MyComponent2 extends Component {
        static template = xml`<div t-ref="active"><button data-hotkey="b" t-on-click="this.onClick">b</button></div>`;
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
    await press("a");
    await press(["alt", "b"]);
    await tick();
    expect.verifySteps(["MyComponent1 subscription", "MyComponent1 [data-hotkey]"]);

    const comp2 = await mountWithCleanup(MyComponent2);
    await press("a");
    await press(["alt", "b"]);
    await tick();
    expect.verifySteps(["MyComponent2 subscription", "MyComponent2 [data-hotkey]"]);

    destroy(comp2);
    await Promise.resolve();
    await press("a");
    await press(["alt", "b"]);
    await tick();
    expect.verifySteps(["MyComponent1 subscription", "MyComponent1 [data-hotkey]"]);
});

test("replace the overlayModifier for non-MacOs", async () => {
    class MyComponent extends Component {
        static template = xml`
            <div>
                <button t-on-click="this.onClick" data-hotkey="b">b</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }
    await mountWithCleanup(MyComponent);
    getService("hotkey").overlayModifier = "alt+shift";
    const key = "b";
    await press(["alt", "shift", key]);
    await tick();
    expect.verifySteps(["click"]);

    await press(["alt", key]);
    expect.verifySteps([]);
});

test("replace the overlayModifier for MacOs", async () => {
    mockUserAgent("mac");

    class MyComponent extends Component {
        static template = xml`
            <div>
            <button t-on-click="this.onClick" data-hotkey="b">b</button>
            </div>
        `;
        static props = ["*"];
        onClick() {
            expect.step("click");
        }
    }
    await mountWithCleanup(MyComponent);
    getService("hotkey").overlayModifier = "alt+shift";

    const key = "b";
    await press(["ctrl", "shift", key]);
    await tick();
    expect.verifySteps(["click"]);

    await press(["ctrl", key]);
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
    await press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".foo").focus();
    await press("ArrowLeft");
    expect.verifySteps([]);
});

test("protects editable elements: can bypassEditableProtection", async () => {
    class Comp extends Component {
        static template = xml`<div><input class="foo"/></div>`;
        static props = ["*"];
        setup() {
            useHotkey("arrowleft", () => expect.step("called"), {
                bypassEditableProtection: true,
            });
        }
    }
    await mountWithCleanup(Comp);

    expect.verifySteps([]);
    await press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".foo").focus();
    await press("ArrowLeft");
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
    await press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".foo").focus();
    await press("ArrowLeft");
    expect.verifySteps(["called"]);

    await contains(".bar").focus();
    await press("ArrowLeft");
    expect.verifySteps([]);
});

test("ignore numpad keys", async () => {
    await makeMockEnv();
    const key = "1";
    getService("hotkey").add(`alt+${key}`, () => expect.step(key));
    await animationFrame();

    await keyDown("alt");

    await press(key, { code: "Numpad1" });
    expect.verifySteps([]);

    await press(key, { code: "Digit1" });
    expect.verifySteps(["1"]);
});

test("within iframes", async () => {
    await makeMockEnv();
    getService("hotkey").add("enter", () => expect.step("called"));
    await animationFrame();

    await press("Enter");
    expect.verifySteps(["called"]);

    const iframe = document.createElement("iframe");
    iframe.srcdoc = "<button>Hello world!</button>";
    const def = new Deferred();
    iframe.onload = def.resolve;
    getFixture().appendChild(iframe);
    await def;

    await contains("iframe:iframe button").focus();
    await press("Enter");
    expect.verifySteps([]);

    getService("hotkey").registerIframe(iframe);
    await press("Enter");
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
                },
            );
        }
    }
    await mountWithCleanup(A);
    await contains(".one").focus();
    await press("Space");
    expect.verifySteps([]);

    await contains(".two").focus();
    await press("Space");
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
                <UIOwnershipTakerComponent t-if="this.state.foo" />
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
                },
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
                },
            );
        }
    }
    const comp = await mountWithCleanup(C);
    expect(getService("ui").activeElement).toBe(document);

    comp.state.foo = true;
    await animationFrame();
    expect(getService("ui").activeElement).toHaveClass("owner");

    await contains(".one").focus();
    await press("Space");
    await press("BackSpace");
    expect.verifySteps([]);

    await contains(".two").focus();
    await press("Space");
    await press("BackSpace");
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
                },
            );
        }
    }
    await mountWithCleanup(A);

    await press("Space");
    expect.verifySteps([]);

    isAvailable = true;
    await press("Space");
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
                { area: () => areaRef.el, isAvailable: () => isAvailable },
            );
        }
    }
    await mountWithCleanup(A);

    await contains(".one").focus();

    isAvailable = false;
    await press("Space");
    expect.verifySteps([]);

    isAvailable = true;
    await press("Space");
    expect.verifySteps([]);

    await contains(".two").focus();

    isAvailable = false;
    await press("Space");
    expect.verifySteps([]);

    isAvailable = true;
    await press("Space");
    expect.verifySteps(["RGNTDJÛ!"]);
});

test("mixing hotkeys with and without operation area", async () => {
    class A extends Component {
        static template = xml`<div class="root" tabindex="0" t-ref="area">root</div>`;
        static props = ["*"];
        setup() {
            const areaRef = useRef("area");
            useHotkey("space", () => expect.step("withoutArea"));
            useHotkey("space", () => expect.step("withArea"), {
                area: () => areaRef.el,
            });
        }
    }
    await mountWithCleanup(A);

    await contains(".root").focus();
    await press("Space");
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

    expect(getActiveHotkey(new KeyboardEvent("keydown", { key: " " }))).toBe("space");

    await mountWithCleanup(A);
    await press([" "]);
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
                },
            );
        }
    }

    await mountWithCleanup(A);

    expect(getOverlays()).toEqual([], { message: "There is no overlay" });

    await keyDown("alt");
    expect(getOverlays()).toEqual(["A"], { message: "should display the overlay" });

    await press("a");
    expect.verifySteps(["hotkey alt+a has been triggered"]);
});

test("hotkey overlay badges respect the active element", async () => {
    class Behind extends Component {
        static template = xml`<div><button class="behind-target">behind</button></div>`;
        static props = ["*"];
        setup() {
            useHotkey("alt+a", () => expect.step("alt+a"), {
                withOverlay: () => queryOne(".behind-target"),
            });
        }
    }
    class Front extends Component {
        static template = xml`<div t-ref="active"><button class="front-target">front</button></div>`;
        static props = ["*"];
        setup() {
            useActiveElement("active");
            useHotkey("alt+b", () => expect.step("alt+b"), {
                withOverlay: () => queryOne(".front-target"),
            });
        }
    }

    await mountWithCleanup(Behind);
    await keyDown("alt");
    expect(getOverlays()).toEqual(["A"], {
        message: "behind is the active element: its badge shows",
    });
    await keyUp("alt");

    await mountWithCleanup(Front);
    await keyDown("alt");
    expect(getOverlays()).toEqual(["B"], {
        message: "front is now the active element: only its badge shows, not behind's",
    });
    await keyUp("alt");
});

test("Support '<' and '>' in hotkeys", async () => {
    class MyComponent extends Component {
        static template = xml``;
        static props = ["*"];
        setup() {
            useHotkey("<", () => expect.step("<"));
            useHotkey(">", () => expect.step(">"));
        }
    }
    await mountWithCleanup(MyComponent);
    await press([">"]);
    expect.verifySteps([">"]);

    await press(["<"]);
    expect.verifySteps(["<"]);
});

test("patching the prototype intercepts a live service instance", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    hotkey.add("q", () => expect.step("callback"));
    await animationFrame();

    patchWithCleanup(HotkeyService.prototype, {
        dispatch(infos) {
            expect.step(`patched:${infos.hotkey}`);
            return super.dispatch(infos);
        },
    });

    await press("q");
    expect.verifySteps(["patched:q", "callback"]);
});

test("the service object's overlayModifier stays live, not snapshotted", async () => {
    await makeMockEnv();
    const hotkey = getService("hotkey");
    patchWithCleanup(hotkeyService, { overlayModifier: "alt+control" });
    hotkey.add("alt+control+q", () => expect.step("combo"), { global: true });
    await animationFrame();

    await press(["alt", "control", "q"]);
    expect.verifySteps(["combo"]);
});
