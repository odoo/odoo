import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { expect, test } from "@odoo/hoot";

class TestModel extends models.Model {
    _name = "test_model";
    doc = fields.Char();
}

defineModels([TestModel]);

test("documentation_link_field: generic url", async () => {
    const url = "https://www.example.com";
    TestModel._records = [{ id: 1, doc: url }];
    await mountView({
        type: "form",
        resModel: "test_model",
        resId: 1,
        arch: /* xml */ `
        <form>
            <field name="doc" widget="documentation_link" />
        </form>`,
    });
    expect(".o_form_uri").toHaveText(url);
    expect(".o_form_uri").toHaveAttribute("href", url);
});

test("documentation_link_field: generic path", async () => {
    const url = "/test";
    TestModel._records = [{ id: 1, doc: url }];
    await mountView({
        type: "form",
        resModel: "test_model",
        resId: 1,
        arch: /* xml */ `
        <form>
            <field name="doc" widget="documentation_link" />
        </form>`,
    });
    expect(".o_form_uri").toHaveText(url);
    expect(".o_form_uri").toHaveAttribute("href", url);
});

test("documentation_link_field: documentation link to latest", async () => {
    const url = "https://www.odoo.com/documentation/latest/test";
    TestModel._records = [{ id: 1, doc: url }];
    await mountView({
        type: "form",
        resModel: "test_model",
        resId: 1,
        arch: /* xml */ `
        <form>
            <field name="doc" widget="documentation_link" />
        </form>`,
    });
    expect(".o_form_uri").toHaveText(url);
    expect(".o_form_uri").toHaveAttribute("href", "/web/documentation/test");
});

test("documentation_link_field: documentation link to a specific version", async () => {
    const url = "https://www.odoo.com/documentation/19.0/test";
    TestModel._records = [{ id: 1, doc: url }];
    await mountView({
        type: "form",
        resModel: "test_model",
        resId: 1,
        arch: /* xml */ `
        <form>
            <field name="doc" widget="documentation_link" />
        </form>`,
    });
    expect(".o_form_uri").toHaveText(url);
    expect(".o_form_uri").toHaveAttribute("href", url);
});
