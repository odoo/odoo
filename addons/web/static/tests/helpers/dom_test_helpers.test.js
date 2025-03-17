import { expect, test } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
import { contains, getMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";

test("contains: all actions", async () => {
    await mountWithCleanup(/* xml */ `
        <div class="container" style="height: 10px; overflow: scroll">
            <button type="button">Click me</button>
            <input type="checkbox" />
            <input type="text" />
            <select>
                <option value="a">A</option>
            </select>
        </div>
    `);

    const CLICK = ["pointerdown", "pointerup", "click"];
    const KEY_PRESS = ["keydown", "keyup"];
    const KEY_PRESS_WITH_CHANGE = ["keydown", "change", "keyup"];

    const actions = [
        // Pointer-based
        ["button", CLICK, (t) => contains(t).click()],
        ["button", ["pointerdown"], (t) => contains(t).drag()],
        ["button", ["pointerdown", "pointerup"], (t) => contains(t).dragAndDrop("button")],
        ["input[type=checkbox]", CLICK, (t) => contains(t).check()],
        ["input[type=checkbox]", CLICK, (t) => contains(t).uncheck()],
        ["button", ["pointerdown", "focus"], (t) => contains(t).focus()],
        ["button", ["pointermove"], (t) => contains(t).hover()],

        // Keyboard-based
        [
            "input[type=text]",
            [
                ...KEY_PRESS, // a
                ...KEY_PRESS_WITH_CHANGE, // Enter
            ],
            (t) => contains(t).edit("a"),
        ],
        [
            "input[type=text]",
            [
                ...KEY_PRESS, // b
                ...KEY_PRESS_WITH_CHANGE, // Enter
            ],
            (t) => contains(t).fill("b"),
        ],
        [
            "input[type=text]",
            [
                ...KEY_PRESS, // Control + a
                ...KEY_PRESS, // Backspace
                ...KEY_PRESS_WITH_CHANGE, // Enter
            ],
            (t) => contains(t).clear(),
        ],
        ["button", ["keydown"], (t) => contains(t).keyDown("a")],
        ["button", ["keyup"], (t) => contains(t).keyUp("a")],
        ["button", KEY_PRESS, (t) => contains(t).press("a")],

        // Other
        [".container", ["scroll"], (t) => contains(t).scroll({ top: 10 })],
        ["select", ["change"], (t) => contains(t).select("a")],
    ];

    if (!getMockEnv().isSmall) {
        actions.unshift([
            "button",
            [...CLICK, ...CLICK, "dblclick"],
            (t) => contains(t).dblclick(),
        ]);
    }

    for (const [target, events, action] of actions) {
        const cleanups = [...new Set(events)].map((event) =>
            on(target, event, () => expect.step(event))
        );

        await action(target);

        cleanups.forEach((cleanup) => cleanup());
        expect.verifySteps(events);
    }
});
