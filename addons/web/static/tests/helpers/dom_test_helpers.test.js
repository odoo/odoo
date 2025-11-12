import { expect, onError, test } from "@odoo/hoot";
import { on } from "@odoo/hoot-dom";
import { Component, useRef, xml } from "@odoo/owl";
import { contains, getMockEnv, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { Dropdown } from "@web/core/dropdown/dropdown";
import { DropdownItem } from "@web/core/dropdown/dropdown_item";
import { useDraggable } from "@web/core/utils/draggable";

test("contains: all actions", async () => {
    class Container extends Component {
        static components = { Dropdown, DropdownItem };
        static props = [];
        static template = xml`
            <div class="container" style="height: 10px; overflow: scroll">
                <button type="button">Click me</button>
                <input type="checkbox" />
                <input type="text" />
                <select>
                    <option value="a">A</option>
                </select>
                <Dropdown>
                    <button>Dropdown</button>
                    <t t-set-slot="content">
                        <DropdownItem class="'item-a'">Item A</DropdownItem>
                        <DropdownItem class="'item-b'">Item B</DropdownItem>
                        <DropdownItem class="'item-c'">Item C</DropdownItem>
                    </t>
                </Dropdown>
            </div>
        `;
    }
    await mountWithCleanup(Container);

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
        [
            ".container",
            ["pointerdown", "pointerup"],
            (t) => contains(t).selectDropdownItem("Item B"),
        ],
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

test("only one drag sequence is allowed at a time", async () => {
    expect.assertions(3);

    await mountWithCleanup(
        class extends Component {
            static components = {};
            static props = {};
            static template = xml`
                <ul t-ref="list">
                    <li>First item</li>
                    <li>Second item</li>
                </ul>
            `;

            setup() {
                useDraggable({
                    ref: useRef("list"),
                    elements: "li",
                    onDragStart() {
                        expect.step("dragstart");
                    },
                    onDragEnd() {
                        if (throwOnDragEnd) {
                            throw new Error("dragend error");
                        } else {
                            expect.step("dragend");
                        }
                    },
                    onDrop() {
                        throw new Error("should not call drop");
                    },
                });
            }
        }
    );

    let throwOnDragEnd = false;

    await contains("li:first").drag();

    expect.verifySteps(["dragstart"]);

    await contains("li:last").drag();

    expect.verifySteps(["dragend", "dragstart"]);

    throwOnDragEnd = true;
    onError((ev) => {
        ev.preventDefault();
        expect(ev.error).toMatch("dragend error", {
            message: "drag sequence should be automatically canceled after test",
        });
    });
});
