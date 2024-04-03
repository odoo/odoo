import { expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import { defineModels, fieldInput, fields, models, mountView, onRpc } from "../../web_test_helpers";

class Contact extends models.Model {
    name = fields.Char();
}

defineModels([Contact]);

const hideTab = () => {
    Object.defineProperty(document, 'visibilityState', {
        value: 'hidden',
    });
    document.dispatchEvent(new Event("visibilitychange"));
    return tick();
}

test("save on hiding tab", async () => {
    Contact._records = [{ id: 1, name: "John Doe" }];
    onRpc("web_save", () => {
        expect.step("save");
    })
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
    });
    expect('.o_field_widget[name="name"] input').toHaveValue("John Doe");
    await fieldInput("name").edit("Jack");
    await hideTab();
    expect(["save"]).toVerifySteps();
});

test("save on hiding tab (not dirty)", async () => {
    Contact._records = [{ id: 1, name: "John Doe" }];
    onRpc("web_save", () => {
        expect.step("save");
    })
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
    });
    await hideTab();
    expect([]).toVerifySteps({ message: "should not have saved" });
});

test("save on hiding tab (invalid field)", async () => {
    onRpc("web_save", () => {
        expect.step("save");
    })
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form><field name="name" required="1"/></form>`,
    });
    await hideTab();
    expect([]).toVerifySteps({ message: "should not save because of invalid field" });
});

test("save only once when hiding tab several times quickly", async () => {
    Contact._records = [{ id: 1, name: "John Doe" }];
    onRpc("web_save", () => {
        expect.step("save");
    })
    await mountView({
        type: "form",
        resModel: "contact",
        arch: `<form><field name="name"/></form>`,
        resId: 1,
    });
    expect('.o_field_widget[name="name"] input').toHaveValue("John Doe");
    await fieldInput("name").edit("Jack");
    await hideTab();
    await hideTab();
    await hideTab();
    expect(["save"]).toVerifySteps({ message: "should have saved, but only once" });
});
