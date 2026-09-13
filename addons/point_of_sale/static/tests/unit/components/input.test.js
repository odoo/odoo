import { expect, test } from "@odoo/hoot";
import { animationFrame } from "@odoo/hoot-dom";
import { advanceTime } from "@odoo/hoot-mock";
import { Component, useState, xml } from "@odoo/owl";
import { Input } from "@point_of_sale/app/components/inputs/input/input";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

test("destroy cancels a debounced input and its callback", async () => {
    const model = { value: "original" };
    const input = await mountWithCleanup(Input, {
        props: {
            tModel: [model, "value"],
            debounceMillis: 500,
            callback: () => expect.step("callback"),
        },
    });
    input.setValue("pending");
    input.__owl__.app.destroy();
    await advanceTime(600);
    expect(model.value).toBe("original");
    expect.verifySteps([]);
});

test("rebinding an input commits pending text to the original model", async () => {
    const original = { value: "original" };
    const replacement = { value: "replacement" };
    let input;
    class Parent extends Component {
        static props = {};
        static components = { Input };
        static template = xml`<Input tModel="[state.model, 'value']" debounceMillis="500" getRef="capture"/>`;
        setup() {
            this.state = useState({ model: original });
        }
        capture(ref) {
            input = ref;
        }
    }
    const parent = await mountWithCleanup(Parent);
    input.el.value = "pending";
    input.el.dispatchEvent(new Event("input", { bubbles: true }));
    parent.state.model = replacement;
    await animationFrame();
    await advanceTime(600);
    expect(original.value).toBe("pending");
    expect(replacement.value).toBe("replacement");
    expect(input.el.value).toBe("replacement");
});

test("pending input uses its original callback when the parent replaces props", async () => {
    let input;
    class Parent extends Component {
        static props = {};
        static components = { Input };
        static template = xml`<Input tModel="[state.model, 'value']" callback="state.callback" debounceMillis="500" getRef="capture"/>`;
        setup() {
            this.state = useState({
                model: { value: "" },
                callback: () => expect.step("old callback"),
            });
        }
        capture(ref) {
            input = ref;
        }
    }
    const parent = await mountWithCleanup(Parent);
    input.el.value = "pending";
    input.el.dispatchEvent(new Event("input", { bubbles: true }));
    parent.state.model = { value: "new" };
    parent.state.callback = () => expect.step("new callback");
    await animationFrame();
    await advanceTime(600);
    expect.verifySteps(["old callback"]);
    expect(parent.state.model.value).toBe("new");
});
