/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { uiService, useActiveElement } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeTestEnv } from "../../helpers/mock_env";
import {
    destroy,
    getFixture,
    mount,
    nextTick,
    patchWithCleanup,
    triggerHotkey,
} from "../../helpers/utils";

const { Component, useState, xml } = owl;
const serviceRegistry = registry.category("services");

let env;
let target;

QUnit.module("Hotkey Service", {
    async beforeEach() {
        serviceRegistry.add("hotkey", hotkeyService);
        serviceRegistry.add("ui", uiService);
        env = await makeTestEnv();
        target = getFixture();
    },
});

QUnit.test("register / unregister", async (assert) => {
    assert.expect(2);

    const hotkey = env.services.hotkey;

    const key = "q";
    triggerHotkey(key);
    await nextTick();

    let removeHotkey = hotkey.add(key, () => assert.step(key));
    await nextTick();

    triggerHotkey(key);
    await nextTick();

    removeHotkey();
    triggerHotkey(key);
    await nextTick();

    assert.verifySteps([key]);
});

QUnit.test("[accesskey] attrs replaced by [data-hotkey]", async (assert) => {
    const div = document.createElement("div");
    div.className = "foo";
    div.accessKey = "a";
    div.onclick = () => assert.step("click");
    div.textContent = "foo";
    target.appendChild(div);

    // div must only have [accesskey] attribute
    assert.containsOnce(target, ".foo");
    assert.containsOnce(target, ".foo[accesskey]");
    assert.containsNone(target, ".foo[data-hotkey]");

    // press any hotkey, i.e. the left arrow
    triggerHotkey("arrowleft");
    await nextTick();

    // div should now only have [data-hotkey] attribute
    assert.containsOnce(target, ".foo");
    assert.containsOnce(target, ".foo[data-hotkey]");
    assert.containsNone(target, ".foo[accesskey]");

    // try to press the related hotkey, just to make sure it works
    assert.verifySteps([]);
    triggerHotkey("a", true);
    await nextTick();
    assert.verifySteps(["click"]);
});

QUnit.test("[accesskey] attrs replaced by [data-hotkey], part 2", async (assert) => {
    class UIOwnershipTakerComponent extends Component {
        setup() {
            useActiveElement("bouh");
        }
    }
    UIOwnershipTakerComponent.template = xml`<p class="owner" t-ref="bouh">bouh</p>`;
    class MyComponent extends Component {
        setup() {
            this.state = useState({ foo: true });
            this.step = assert.step.bind(assert);
        }
    }
    MyComponent.components = { UIOwnershipTakerComponent };
    MyComponent.template = xml`
        <main>
            <UIOwnershipTakerComponent t-if="state.foo" />
            <div t-on-click="() => { this.step('click'); }" accesskey="a">foo</div>
        </main>
    `;
    const comp = await mount(MyComponent, target, { env });

    // UIOwnershipTakerComponent should be there and it should be the ui active element
    assert.containsOnce(target, "main .owner");
    assert.strictEqual(target.querySelector("main .owner"), env.services.ui.activeElement);

    // div must only have [accesskey] attribute
    assert.containsOnce(target, "main div");
    assert.containsOnce(target, "main div[accesskey]");
    assert.containsNone(target, "main div[data-hotkey]");

    // press any hotkey, i.e. the left arrow
    triggerHotkey("arrowleft");
    await nextTick();

    // div should now only have [data-hotkey] attribute
    assert.containsOnce(target, "main div");
    assert.containsOnce(target, "main div[data-hotkey]");
    assert.containsNone(target, "main div[accesskey]");

    // try to press the related hotkey, it should not work as the ui active element is different
    assert.notEqual(
        env.services.ui.getActiveElementOf(target.querySelector("main div")),
        env.services.ui.activeElement
    );
    assert.verifySteps([]);
    triggerHotkey("a", true);
    await nextTick();
    assert.verifySteps([]);

    // remove the UIOwnershipTakerComponent
    comp.state.foo = false;
    await nextTick();
    assert.strictEqual(
        env.services.ui.getActiveElementOf(target.querySelector("main div")),
        env.services.ui.activeElement
    );

    assert.containsNone(target, "main .owner");
    assert.containsOnce(target, "main div");
    assert.containsOnce(target, "main div[data-hotkey]");
    assert.containsNone(target, "main div[accesskey]");

    assert.verifySteps([]);
    triggerHotkey("a", true);
    await nextTick();
    assert.verifySteps(["click"]);
});

QUnit.test("data-hotkey", async (assert) => {
    assert.expect(2);

    class MyComponent extends Component {
        onClick() {
            assert.step("click");
        }
    }
    MyComponent.template = xml`
    <div>
      <button t-on-click="onClick" data-hotkey="b" />
    </div>
  `;

    const key = "b";
    triggerHotkey(key, true);
    await nextTick();

    const comp = await mount(MyComponent, target, { env });

    triggerHotkey(key, true);
    await nextTick();

    destroy(comp);

    triggerHotkey(key, true);
    await nextTick();

    assert.verifySteps(["click"]);
});

QUnit.test("invisible data-hotkeys are not enabled. ", async (assert) => {
    assert.expect(3);

    class MyComponent extends Component {
        onClick() {
            assert.step("click");
        }
    }
    MyComponent.template = xml`
        <div>
        <button t-on-click="onClick" data-hotkey="b" class="myButton"/>
        </div>
    `;

    const key = "b";
    triggerHotkey(key, true);
    await nextTick();

    await mount(MyComponent, target, { env });

    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps(["click"]);

    target.querySelector(".myButton").disabled = true;
    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps([], "shouldn't trigger the hotkey of an invisible button");
});

QUnit.test("hook", async (assert) => {
    const key = "q";
    class TestComponent extends Component {
        setup() {
            useHotkey(key, () => assert.step(key));
        }
    }
    TestComponent.template = xml`<div/>`;

    triggerHotkey(key);
    await nextTick();

    const comp = await mount(TestComponent, target, { env });

    triggerHotkey(key);
    await nextTick();

    destroy(comp);

    triggerHotkey(key);
    await nextTick();

    assert.verifySteps([key]);
});

QUnit.test("non-MacOS usability", async (assert) => {
    assert.expect(6);

    const hotkey = env.services.hotkey;
    const key = "q";

    // On non-MacOS, ALT is NOT replaced by CONTROL key
    let removeHotkey = hotkey.add(`alt+${key}`, () => assert.step(`alt+${key}`));
    await nextTick();

    let keydown = new KeyboardEvent("keydown", { key, altKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([`alt+${key}`]);

    keydown = new KeyboardEvent("keydown", { key, ctrlKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([]);

    removeHotkey();

    // On non-MacOS, CONTROL is NOT replaced by COMMAND key (= metaKey)
    removeHotkey = hotkey.add(`control+${key}`, () => assert.step(`control+${key}`));
    await nextTick();

    keydown = new KeyboardEvent("keydown", { key, ctrlKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([`control+${key}`]);

    keydown = new KeyboardEvent("keydown", { key, metaKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([]);

    removeHotkey();
});

QUnit.test("the overlay of hotkeys is correctly displayed", async (assert) => {
    assert.expect(7);

    const displayHotkeysOverlay = () =>
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "alt", altKey: true }));

    class MyComponent extends Component {
        onClick(ev) {
            assert.step(`click ${ev.target.dataset.hotkey}`);
        }
    }
    MyComponent.template = xml`
        <div>
        <button t-on-click="onClick" data-hotkey="b"/>
        <button t-on-click="onClick" data-hotkey="c"/>
        </div>
    `;
    await mount(MyComponent, target, { env });
    const getOverlays = () =>
        [...target.querySelectorAll(".o_web_hotkey_overlay")].map((el) => el.innerText);

    displayHotkeysOverlay();
    assert.deepEqual(getOverlays(), ["B", "C"], "should display the overlay");

    // apply an existent hotkey
    triggerHotkey(`alt+b`);
    await nextTick();
    assert.verifySteps(["click b"]);
    assert.deepEqual(getOverlays(), [], "shouldn't display the overlay");

    displayHotkeysOverlay();
    assert.deepEqual(getOverlays(), ["B", "C"], "should display the overlay");

    // apply a non-existent hotkey
    triggerHotkey(`alt+x`);
    await nextTick();
    assert.deepEqual(getOverlays(), [], "shouldn't display the overlay");
    assert.verifySteps([]);
});

QUnit.test("the overlay of hotkeys is correctly displayed on MacOs", async (assert) => {
    assert.expect(7);

    patchWithCleanup(browser, {
        navigator: {
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(MacOs)"),
        },
    });

    const displayHotkeysOverlay = () =>
        window.dispatchEvent(new KeyboardEvent("keydown", { key: "control", ctrlKey: true }));

    class MyComponent extends Component {
        onClick(ev) {
            assert.step(`click ${ev.target.dataset.hotkey}`);
        }
    }
    MyComponent.template = xml`
        <div>
        <button t-on-click="onClick" data-hotkey="b"/>
        <button t-on-click="onClick" data-hotkey="c"/>
        </div>
    `;
    await mount(MyComponent, target, { env });
    const getOverlays = () =>
        [...target.querySelectorAll(".o_web_hotkey_overlay")].map((el) => el.innerText);

    displayHotkeysOverlay();
    assert.deepEqual(getOverlays(), ["B", "C"], "should display the overlay");

    // apply an existent hotkey
    triggerHotkey(`alt+b`);
    await nextTick();
    assert.verifySteps(["click b"]);
    assert.deepEqual(getOverlays(), [], "shouldn't display the overlay");

    displayHotkeysOverlay();
    assert.deepEqual(getOverlays(), ["B", "C"], "should display the overlay");

    // apply a non-existent hotkey
    triggerHotkey(`alt+x`);
    await nextTick();
    assert.deepEqual(getOverlays(), [], "shouldn't display the overlay");
    assert.verifySteps([]);
});

QUnit.test("overlays can be toggled multiple times in a row", async (assert) => {
    const eventArgs = { key: "alt", altKey: true, bubbles: true };
    const pressOverlayModifier = () =>
        document.activeElement.dispatchEvent(new KeyboardEvent("keydown", eventArgs));
    const releaseOverlayModifier = () =>
        document.activeElement.dispatchEvent(new KeyboardEvent("keyup", eventArgs));

    class MyComponent extends Component {}
    MyComponent.template = xml`<button data-hotkey="a"/>`;

    await mount(MyComponent, target, { env });
    assert.containsNone(target, ".o_web_hotkey_overlay");

    // Display overlays
    pressOverlayModifier();
    await nextTick();
    assert.containsOnce(target, ".o_web_hotkey_overlay");

    // Hide overlays
    releaseOverlayModifier();
    await nextTick();
    assert.containsNone(target, ".o_web_hotkey_overlay");

    // Display overlays
    pressOverlayModifier();
    await nextTick();
    assert.containsOnce(target, ".o_web_hotkey_overlay");

    // Hide overlays
    releaseOverlayModifier();
    await nextTick();
    assert.containsNone(target, ".o_web_hotkey_overlay");
});

QUnit.test("MacOS usability", async (assert) => {
    assert.expect(6);

    patchWithCleanup(browser, {
        navigator: {
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(MacOs)"),
        },
    });

    const hotkey = env.services.hotkey;
    const key = "q";

    // On MacOS, ALT is replaced by CONTROL key
    let removeHotkey = hotkey.add(`alt+${key}`, () => assert.step(`alt+${key}`));
    await nextTick();

    let keydown = new KeyboardEvent("keydown", { key, altKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([]);

    keydown = new KeyboardEvent("keydown", { key, ctrlKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([`alt+${key}`]);

    removeHotkey();

    // On MacOS, CONTROL is replaced by COMMAND key (= metaKey)
    removeHotkey = hotkey.add(`control+${key}`, () => assert.step(`control+${key}`));
    await nextTick();

    keydown = new KeyboardEvent("keydown", { key, ctrlKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([]);

    keydown = new KeyboardEvent("keydown", { key, metaKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([`control+${key}`]);

    removeHotkey();
});

QUnit.test("[data-hotkey] alt is required", async (assert) => {
    const key = "a";
    class TestComponent extends Component {
        onClick() {
            assert.step(key);
        }
    }
    TestComponent.template = xml`<div><button t-on-click="onClick" data-hotkey="${key}"/></div>`;

    await mount(TestComponent, target, { env });

    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps([key]);

    triggerHotkey(key);
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("registration allows repeat if specified", async (assert) => {
    assert.expect(6);

    const allowRepeatKey = "a";
    const disallowRepeatKey = "b";
    const defaultBehaviourKey = "c";

    env.services.hotkey.add(allowRepeatKey, () => assert.step(allowRepeatKey), {
        allowRepeat: true,
    });
    env.services.hotkey.add(disallowRepeatKey, () => assert.step(disallowRepeatKey), {
        allowRepeat: false,
    });
    env.services.hotkey.add(defaultBehaviourKey, () => assert.step(defaultBehaviourKey));
    await nextTick();

    // Dispatch the three keys without repeat:
    triggerHotkey(allowRepeatKey);
    triggerHotkey(disallowRepeatKey);
    triggerHotkey(defaultBehaviourKey);
    await nextTick();

    assert.verifySteps([allowRepeatKey, disallowRepeatKey, defaultBehaviourKey]);

    // Dispatch the three keys with repeat:
    triggerHotkey(allowRepeatKey, false, { repeat: true });
    triggerHotkey(disallowRepeatKey, false, { repeat: true });
    triggerHotkey(defaultBehaviourKey, false, { repeat: true });
    await nextTick();

    assert.verifySteps([allowRepeatKey]);
});

QUnit.test("[data-hotkey] never allow repeat", async (assert) => {
    assert.expect(3);
    const key = "a";
    class TestComponent extends Component {
        onClick() {
            assert.step(key);
        }
    }
    TestComponent.template = xml`<div><button t-on-click="onClick" data-hotkey="${key}"/></div>`;

    await mount(TestComponent, target, { env });

    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps([key]);

    triggerHotkey(key, true, { repeat: true });
    await nextTick();
    assert.verifySteps([]);
});

QUnit.test("hotkeys evil 👹", async (assert) => {
    const hotkey = env.services.hotkey;

    assert.throws(function () {
        hotkey.add();
    }, /must specify an hotkey/);
    assert.throws(function () {
        hotkey.add(null);
    }, /must specify an hotkey/);

    function callback() {}
    assert.throws(function () {
        hotkey.add(null, callback);
    }, /must specify an hotkey/);
    assert.throws(function () {
        hotkey.add("");
    }, /must specify an hotkey/);
    assert.throws(function () {
        hotkey.add("crap", callback);
    }, /not whitelisted/);
    assert.throws(function () {
        hotkey.add("ctrl+o", callback);
    }, /not whitelisted/);
    assert.throws(function () {
        hotkey.add("Control+o");
    }, /specify a callback/);
    assert.throws(function () {
        hotkey.add("Control+o+d", callback);
    }, /more than one single key part/);
});

QUnit.test("component can register many hotkeys", async (assert) => {
    assert.expect(4);

    class MyComponent extends Component {
        setup() {
            useHotkey("a", () => assert.step("callback:a"));
            useHotkey("b", () => assert.step("callback:b"));
        }
        onClick() {
            assert.step("click");
        }
    }
    MyComponent.template = xml`<div><button t-on-click="onClick" data-hotkey="c"/></div>`;

    await mount(MyComponent, target, { env });
    triggerHotkey("a");
    triggerHotkey("b");
    triggerHotkey("c", true);
    await nextTick();

    assert.verifySteps(["callback:a", "callback:b", "click"]);
});

QUnit.test("many components can register same hotkeys (call order matters)", async (assert) => {
    assert.expect(13);
    const getComp = (name) => {
        const Comp = class extends Component {
            setup() {
                useHotkey("a", () => assert.step(`${name}:a`));
                useHotkey("b", () => assert.step(`${name}:b`));
                useHotkey("alt+z", () => assert.step(`${name}:z`));
            }
            onClick(ev) {
                assert.step(`${name}:${ev.target.dataset.hotkey}:button`);
            }
        };
        Comp.template = xml`
            <div>
                <button t-on-click="onClick" data-hotkey="c"/>
                <button t-on-click="onClick" data-hotkey="z"/>
            </div>
        `;
        return Comp;
    };
    await mount(getComp("comp1"), target, { env });
    triggerHotkey("a");
    triggerHotkey("b");
    triggerHotkey("c", true);
    await nextTick();
    assert.verifySteps(
        ["comp1:a", "comp1:b", "comp1:c:button"],
        "the callbacks of comp1 are called"
    );

    triggerHotkey("z", true);
    await nextTick();
    assert.verifySteps(
        ["comp1:z"],
        "calls only the callback from the useHotkey registration and the button is not clicked"
    );

    await mount(getComp("comp2"), target, { env });
    triggerHotkey("a");
    triggerHotkey("b");
    await nextTick();
    assert.verifySteps(
        ["comp2:a", "comp2:b"],
        "calls only the callbacks from last useHotkey registrations"
    );

    triggerHotkey("c", true);
    await nextTick();
    assert.verifySteps(
        ["comp1:c:button"],
        "calls only the callback of the first encountered button with proper [data-hotkey]"
    );

    triggerHotkey("z", true);
    await nextTick();
    assert.verifySteps(
        ["comp2:z"],
        "calls only the callbacks from last useHotkey registrations and no button is clicked"
    );
});

QUnit.test("registrations and elements belong to the correct UI owner", async (assert) => {
    assert.expect(7);
    class MyComponent1 extends Component {
        setup() {
            useHotkey("a", () => assert.step("MyComponent1 subscription"));
        }
        onClick() {
            assert.step("MyComponent1 [data-hotkey]");
        }
    }
    MyComponent1.template = xml`<div><button data-hotkey="b" t-on-click="onClick"/></div>`;

    class MyComponent2 extends Component {
        setup() {
            useHotkey("a", () => assert.step("MyComponent2 subscription"));
            useActiveElement("active");
        }
        onClick() {
            assert.step("MyComponent2 [data-hotkey]");
        }
    }
    MyComponent2.template = xml`<div t-ref="active"><button data-hotkey="b" t-on-click="onClick"/></div>`;

    await mount(MyComponent1, target, { env });
    triggerHotkey("a");
    triggerHotkey("b", true);
    await nextTick();

    const comp2 = await mount(MyComponent2, target, { env });
    triggerHotkey("a");
    triggerHotkey("b", true);
    await nextTick();

    destroy(comp2);
    triggerHotkey("a");
    triggerHotkey("b", true);
    await nextTick();

    assert.verifySteps([
        "MyComponent1 subscription",
        "MyComponent1 [data-hotkey]",
        "MyComponent2 subscription",
        "MyComponent2 [data-hotkey]",
        "MyComponent1 subscription",
        "MyComponent1 [data-hotkey]",
    ]);
});

QUnit.test("replace the overlayModifier for non-MacOs", async (assert) => {
    assert.expect(3);

    const hotkeyService = serviceRegistry.get("hotkey");
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+shift",
    });

    class MyComponent extends Component {
        onClick() {
            assert.step("click");
        }
    }
    MyComponent.template = xml`
        <div>
        <button t-on-click="onClick" data-hotkey="b"/>
        </div>
    `;
    await mount(MyComponent, target, { env });

    const key = "b";
    triggerHotkey(`alt+shift+${key}`);

    await nextTick();
    assert.verifySteps(["click"]);

    triggerHotkey(`alt+${key}`);
    await nextTick();

    assert.verifySteps([]);
});

QUnit.test("replace the overlayModifier for MacOs", async (assert) => {
    assert.expect(3);

    patchWithCleanup(browser, {
        navigator: {
            userAgent: browser.navigator.userAgent.replace(/\([^)]*\)/, "(MacOs)"),
        },
    });

    const hotkeyService = serviceRegistry.get("hotkey");
    patchWithCleanup(hotkeyService, {
        overlayModifier: "alt+shift",
    });

    class MyComponent extends Component {
        onClick() {
            assert.step("click");
        }
    }
    MyComponent.template = xml`
        <div>
        <button t-on-click="onClick" data-hotkey="b"/>
        </div>
    `;
    await mount(MyComponent, target, { env });

    const key = "b";
    triggerHotkey(`alt+shift+${key}`);

    await nextTick();
    assert.verifySteps(["click"]);

    triggerHotkey(`alt+${key}`);
    await nextTick();

    assert.verifySteps([]);
});

QUnit.test("protects editable elements", async (assert) => {
    assert.expect(4);
    class Comp extends Component {
        setup() {
            useHotkey("arrowleft", () => assert.step("called"));
        }
    }
    Comp.template = xml`<div><input class="foo"/></div>`;
    await mount(Comp, target, { env });
    const input = target.querySelector(".foo");

    assert.verifySteps([]);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(["called"]);

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(
        [],
        "the callback is not getting called when it is triggered from an editable"
    );
});

QUnit.test("protects editable elements: can bypassEditableProtection", async (assert) => {
    assert.expect(5);
    class Comp extends Component {
        setup() {
            useHotkey("arrowleft", () => assert.step("called"), { bypassEditableProtection: true });
        }
    }
    Comp.template = xml`<div><input class="foo"/></div>`;
    await mount(Comp, target, { env });
    const input = target.querySelector(".foo");

    assert.verifySteps([]);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(["called"]);

    input.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(
        ["called"],
        "the callback still gets called even if triggered from an editable"
    );
});

QUnit.test("protects editable elements: an editable can allow hotkeys", async (assert) => {
    class Comp extends Component {
        setup() {
            useHotkey("arrowleft", () => assert.step("called"));
        }
    }
    Comp.template = xml`<div><input class="foo" data-allow-hotkeys="true"/><input class="bar"/></div>`;
    await mount(Comp, target, { env });
    const fooInput = target.querySelector(".foo");
    const barInput = target.querySelector(".bar");

    assert.verifySteps([]);
    document.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(["called"]);

    fooInput.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(["called"], "the callback gets called as the foo editable allows it");

    barInput.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowLeft", bubbles: true }));
    await nextTick();
    assert.verifySteps(
        [],
        "the callback does not get called as the bar editable does not explicitly allow hotkeys"
    );
});

QUnit.test("ignore numpad keys", async (assert) => {
    assert.expect(3);

    const key = "1";

    env.services.hotkey.add(`alt+${key}`, () => assert.step(key));
    await nextTick();

    let keydown = new KeyboardEvent("keydown", { key, code: "Numpad1", altKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps([]);

    keydown = new KeyboardEvent("keydown", { key: "&", code: "Digit1", altKey: true });
    window.dispatchEvent(keydown);
    await nextTick();
    assert.verifySteps(["1"]);
});
