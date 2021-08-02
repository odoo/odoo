/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { useHotkey } from "@web/core/hotkeys/hotkey_hook";
import { registry } from "@web/core/registry";
import { uiService, useActiveElement } from "@web/core/ui/ui_service";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { makeTestEnv } from "../../helpers/mock_env";
import { getFixture, nextTick, patchWithCleanup, triggerHotkey } from "../../helpers/utils";

const { Component, mount, tags } = owl;
const { xml } = tags;
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

    const comp = await mount(MyComponent, { env, target });

    triggerHotkey(key, true);
    await nextTick();

    comp.unmount();

    triggerHotkey(key, true);
    await nextTick();

    assert.verifySteps(["click"]);
    comp.destroy();
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

    const comp = await mount(MyComponent, { env, target });

    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps(["click"]);

    comp.el.querySelector(".myButton").disabled = true;
    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps([], "shouldn't trigger the hotkey of an invisible button");

    comp.destroy();
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

    const comp = await mount(TestComponent, { env, target });

    triggerHotkey(key);
    await nextTick();

    comp.unmount();

    triggerHotkey(key);
    await nextTick();

    assert.verifySteps([key]);
    comp.destroy();
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
    const comp = await mount(MyComponent, { env, target });
    const getOverlays = () =>
        [...comp.el.querySelectorAll(".o_web_hotkey_overlay")].map((el) => el.innerText);

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
    const comp = await mount(MyComponent, { env, target });
    const getOverlays = () =>
        [...comp.el.querySelectorAll(".o_web_hotkey_overlay")].map((el) => el.innerText);

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

    const comp = await mount(TestComponent, { env, target });

    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps([key]);

    triggerHotkey(key);
    await nextTick();
    assert.verifySteps([]);

    comp.destroy();
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

    const comp = await mount(TestComponent, { env, target });

    triggerHotkey(key, true);
    await nextTick();
    assert.verifySteps([key]);

    triggerHotkey(key, true, { repeat: true });
    await nextTick();
    assert.verifySteps([]);

    comp.destroy();
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
    assert.expect(8);

    class MyComponent extends Component {
        setup() {
            for (const hotkey of ["a", "b", "c"]) {
                useHotkey(`alt+${hotkey}`, () => assert.step(`callback:${hotkey}`));
            }
            for (const hotkey of ["d", "e", "f"]) {
                useHotkey(hotkey, () => assert.step(`callback2:${hotkey}`));
            }
        }
        onClick() {
            assert.step("click");
        }
    }
    MyComponent.template = xml`
    <div>
      <button t-on-click="onClick" data-hotkey="b" />
    </div>
  `;

    const comp = await mount(MyComponent, { env, target });
    triggerHotkey("a", true);
    triggerHotkey("b", true);
    triggerHotkey("c", true);
    triggerHotkey("d");
    triggerHotkey("e");
    triggerHotkey("f");
    await nextTick();

    assert.verifySteps([
        "callback:a",
        "callback:b",
        "click",
        "callback:c",
        "callback2:d",
        "callback2:e",
        "callback2:f",
    ]);
    comp.destroy();
});

QUnit.test("many components can register same hotkeys", async (assert) => {
    assert.expect(1);

    const result = [];
    const hotkeys = ["a", "b", "c"];

    class MyComponent1 extends Component {
        setup() {
            for (const hotkey of hotkeys) {
                useHotkey(`alt+${hotkey}`, () => result.push(`comp1:${hotkey}`));
            }
        }
        onClick() {
            result.push("comp1:click");
        }
    }
    MyComponent1.template = xml`
    <div>
      <button t-on-click="onClick" data-hotkey="b" />
    </div>
  `;

    class MyComponent2 extends Component {
        setup() {
            for (const hotkey of hotkeys) {
                useHotkey(`alt+${hotkey}`, () => result.push(`comp2:${hotkey}`));
            }
        }
        onClick() {
            result.push("comp2:click");
        }
    }
    MyComponent2.template = xml`
    <div>
      <button t-on-click="onClick" data-hotkey="b" />
    </div>
  `;

    const comp1 = await mount(MyComponent1, { env, target });
    const comp2 = await mount(MyComponent2, { env, target });
    triggerHotkey("a", true);
    triggerHotkey("b", true);
    triggerHotkey("c", true);
    await nextTick();

    assert.deepEqual(result.sort(), [
        "comp1:a",
        "comp1:b",
        "comp1:c",
        "comp1:click",
        "comp2:a",
        "comp2:b",
        "comp2:c",
        "comp2:click",
    ]);
    comp1.destroy();
    comp2.destroy();
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
    MyComponent1.template = xml`<div><button data-hotkey="b" t-on-click="onClick()"/></div>`;

    class MyComponent2 extends Component {
        setup() {
            useHotkey("a", () => assert.step("MyComponent2 subscription"));
            useActiveElement();
        }
        onClick() {
            assert.step("MyComponent2 [data-hotkey]");
        }
    }
    MyComponent2.template = xml`<div><button data-hotkey="b" t-on-click="onClick()"/></div>`;

    const comp1 = await mount(MyComponent1, { env, target });
    triggerHotkey("a");
    triggerHotkey("b", true);
    await nextTick();

    const comp2 = await mount(MyComponent2, { env, target });
    triggerHotkey("a");
    triggerHotkey("b", true);
    await nextTick();

    comp2.unmount();
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

    comp1.destroy();
    comp2.destroy();
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
    await mount(MyComponent, { env, target });

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
    await mount(MyComponent, { env, target });

    const key = "b";
    triggerHotkey(`alt+shift+${key}`);

    await nextTick();
    assert.verifySteps(["click"]);

    triggerHotkey(`alt+${key}`);
    await nextTick();

    assert.verifySteps([]);
});
