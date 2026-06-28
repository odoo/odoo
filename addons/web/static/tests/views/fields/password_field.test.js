import { expect, test } from "@odoo/hoot";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    name = fields.Char({ string: "Name" });
    bio = fields.Text({ string: "Bio" });
    _records = [{ id: 1, name: "secret", bio: "my long bio" }];
}

defineModels([Partner]);

onRpc("res.users", "has_group", () => true);

test("PasswordField: readonly in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="name" widget="password" readonly="1"/></form>`,
    });

    expect(".o_field_password input[type=password].o_disabled").toHaveCount(1);
    await contains(".o_field_password button.fa-eye").click();
    expect(".o_field_password button.fa-eye-slash").toHaveCount(1);
    expect(".o_field_password input").toHaveCount(0);
    expect(".o_field_password span").toHaveText("secret");
});

test("PasswordField: edition in form view", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1].name);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="name" widget="password"/></form>`,
    });

    // edit while hidden
    expect(".o_field_password input[type=password]").toHaveCount(1);
    await contains(".o_field_password input").edit("newsecret1");
    await clickSave();

    // reveal and edit
    await contains(".o_field_password button.fa-eye").click();
    expect(".o_field_password input[type=text]").toHaveValue("newsecret1");
    await contains(".o_field_password input").edit("newsecret2");
    await clickSave();

    expect.verifySteps(["newsecret1", "newsecret2"]);
});

test("PasswordField in non-editable list view", async () => {
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list><field name="name" widget="password"/></list>`,
    });

    expect(".o_field_password input[type=password].o_disabled").toHaveCount(1);
    await contains(".o_field_password button.fa-eye").click();
    expect(".o_field_password button.fa-eye-slash").toHaveCount(1);
    expect(".o_field_password input").toHaveCount(0);
    expect(".o_field_password span").toHaveText("secret");
});

test("PasswordField: edition in editable list view", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1].name);
    });
    await mountView({
        type: "list",
        resModel: "partner",
        arch: `<list editable="bottom"><field name="name" widget="password"/></list>`,
    });

    expect(".o_field_password input[type=password].o_disabled").toHaveCount(1);
    await contains(".o_data_row td.o_data_cell").click();
    expect(".o_field_password input[type=password]:not([disabled])").toHaveCount(1);
    await contains(".o_field_password button.fa-eye").click();
    expect(".o_field_password input[type=text]").toHaveValue("secret");
    await contains(".o_field_password input").edit("newsecret");

    expect.verifySteps(["newsecret"]);
});

test("PasswordField: placeholder attribute", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: `<form><field name="name" widget="password" placeholder="Enter password"/></form>`,
    });
    expect(".o_field_password input").toHaveAttribute("placeholder", "Enter password");
});

test("PasswordField on readonly text field in form view", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="bio" widget="password" readonly="1"/></form>`,
    });

    expect(".o_field_password input[type=password].o_disabled").toHaveCount(1);
    await contains(".o_field_password button.fa-eye").click();
    expect(".o_field_password button.fa-eye-slash").toHaveCount(1);
    expect(".o_field_password input").toHaveCount(0);
    expect(".o_field_password span").toHaveText("my long bio");
});

test("PasswordField on text field: edition in form view", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1].bio);
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `<form><field name="bio" widget="password"/></form>`,
    });

    expect(".o_field_password input[type=password]").toHaveCount(1);
    await contains(".o_field_password button.fa-eye").click();
    expect(".o_field_password input[type=text]").toHaveValue("my long bio");
    await contains(".o_field_password input").edit("updated bio");
    await clickSave();

    expect.verifySteps(["updated bio"]);
});
