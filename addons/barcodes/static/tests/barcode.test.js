/** @odoo-module **/

import { Macro } from "@web/core/macro";
import { beforeEach, expect, test } from "@odoo/hoot";
import { advanceTime, animationFrame, press } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

async function simulateBarCode(chars) {
    for (const char of chars) {
        await press(char);
    }
}

class Product extends models.Model {
    name = fields.Char({ string: "Product name" });
    int_field = fields.Integer({ string: "Integer" });
    int_field_2 = fields.Integer({ string: "Integer" });
    barcode = fields.Char({ string: "Barcode" });
    _records = [
        { id: 1, name: "Large Cabinet", barcode: "1234567890" },
        { id: 2, name: "Cabinet with Doors", barcode: "0987654321" },
    ];
}

defineModels([Product]);

let macro;
async function macroIsComplete() {
    while (!macro.isComplete) {
        await advanceTime(100);
    }
}

beforeEach(() => {
    patchWithCleanup(Macro.prototype, {
        start() {
            super.start(...arguments);
            macro = this;
        },
    });
});

test.tags("desktop");
test("Button with barcode_trigger", async () => {
    mockService("action", {
        doActionButton: (data) => {
            expect.step(data.name);
        },
    });

    mockService("notification", {
        add: (params) => {
            expect.step(params.type);
        },
    });
    await mountView({
        type: "form",
        resModel: "product",
        arch: `<form>
                    <header>
                        <button name="do_something" string="Validate" type="object" barcode_trigger="DOIT"/>
                        <button name="do_something_else" string="Validate" type="object" invisible="1" barcode_trigger="DOTHAT"/>
                    </header>
                </form>`,
        resId: 2,
    });
    // OBTDOIT
    await simulateBarCode(["O", "B", "T", "D", "O", "I", "T", "Enter"]);
    // OBTDOTHAT (should not call execute_action as the button isn't visible)
    await simulateBarCode(["O", "B", "T", "D", "O", "T", "H", "A", "T", "Enter"]);
    expect.verifySteps(["do_something"]);
});

test.tags("desktop");
test("Two buttons with same barcode_trigger and the same string and action", async () => {
    mockService("action", {
        doActionButton: (data) => {
            expect.step(data.name);
        },
    });

    mockService("notification", {
        add: (params) => {
            expect.step(params.type);
        },
    });
    await mountView({
        type: "form",
        resModel: "product",
        arch: `<form>
                <header>
                    <button name="do_something" string="Validate" type="object" invisible="0" barcode_trigger="DOIT"/>
                    <button name="do_something" string="Validate" type="object" invisible="1" barcode_trigger="DOIT"/>
                </header>
            </form>`,
        resId: 2,
    });
    // OBTDOIT should call execute_action as the first button is visible
    await simulateBarCode(["O", "B", "T", "D", "O", "I", "T", "Enter"]);
    await animationFrame();
    expect.verifySteps(["do_something"]);
});

test.tags("desktop");
test("edit, save and cancel buttons", async () => {
    onRpc("web_save", () => expect.step("save"));
    await mountView({
        type: "form",
        resModel: "product",
        arch: '<form><field name="name"/></form>',
        resId: 1,
    });

    // OCDEDIT
    await simulateBarCode(["O", "C", "D", "E", "D", "I", "T", "Enter"]);
    // dummy change to check that it actually saves
    await contains(".o_field_widget input").edit("test", { confirm: "blur" });

    // OCDSAVE
    await simulateBarCode(["O", "C", "D", "S", "A", "V", "E", "Enter"]);
    expect.verifySteps(["save"]);

    // OCDEDIT
    await simulateBarCode(["O", "C", "D", "E", "D", "I", "T", "Enter"]);
    // dummy change to check that it correctly discards
    await contains(".o_field_widget input").edit("test", { confirm: "blur" });
    // OCDDISC
    await simulateBarCode(["O", "C", "D", "D", "I", "S", "C", "Enter"]);
    expect.verifySteps([]);
});

test.tags("desktop");
test("pager buttons", async () => {
    await mountView({
        type: "form",
        resModel: "product",
        arch: '<form><field name="name"/></form>',
        resId: 1,
        resIds: [1, 2],
    });

    expect(".o_field_widget input").toHaveValue("Large Cabinet");
    // OCDNEXT
    await simulateBarCode(["O", "C", "D", "N", "E", "X", "T", "Enter"]);
    await animationFrame();
    expect(".o_field_widget input").toHaveValue("Cabinet with Doors");

    // OCDPREV
    await simulateBarCode(["O", "C", "D", "P", "R", "E", "V", "Enter"]);
    await animationFrame();
    expect(".o_field_widget input").toHaveValue("Large Cabinet");

    // OCDPAGERLAST
    await simulateBarCode(["O", "C", "D", "P", "A", "G", "E", "R", "L", "A", "S", "T", "Enter"]);
    // need to await 2 macro steps
    await macroIsComplete();
    expect(".o_field_widget input").toHaveValue("Cabinet with Doors");

    // OCDPAGERFIRST
    await simulateBarCode([
        "O",
        "C",
        "D",
        "P",
        "A",
        "G",
        "E",
        "R",
        "F",
        "I",
        "R",
        "S",
        "T",
        "Enter",
    ]);
    // need to await 2 macro steps
    await macroIsComplete();
    expect(".o_field_widget input").toHaveValue("Large Cabinet");
});
