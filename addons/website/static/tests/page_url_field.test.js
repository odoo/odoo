import { defineMailModels } from "@mail/../tests/mail_test_helpers";
import { advanceTime, expect, freezeTime, test, waitFor, waitForNone } from "@odoo/hoot";
import {
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Product extends models.Model {
    url = fields.Char({
        onChange(record) {
            // factice onchange to cause onchange calls
        },
    });
    old_url = fields.Char();
}

defineModels([Product]);
defineMailModels();

test("PageUrlField in form view", async () => {
    freezeTime();
    Product._records = [{ id: 1, url: "/test", old_url: "/test" }];
    onRpc("onchange", ({ args }) => {
        expect.step(`onchange ${args[1].url}`);
    });
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form>
                   <field name="url" widget="page_url"/>
                   <field name="old_url"/>
                   <div invisible="old_url == url" id="changed">
                       CHANGED
                   </div>
               </form>`,
    });
    expect(`.o_field_widget input#url_0`).toHaveValue("test");
    expect(`#changed`).toHaveCount(0);
    await fieldInput("url").press("a");
    await fieldInput("url").press("b");
    expect(`#changed`).toHaveCount(0);
    await advanceTime(100); // debounce
    await waitFor(`#changed`); // onchange + render
    expect.verifySteps(["onchange /testab"]);

    await fieldInput("url").press("Backspace");
    await fieldInput("url").press("Backspace");
    expect(`#changed`).toHaveCount(1);
    await advanceTime(100); // debounce
    await waitForNone(`#changed`); // onchange + render
    expect.verifySteps(["onchange /test"]);
});
