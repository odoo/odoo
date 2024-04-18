import { defineModels, fields, models, mountView } from "@web/../tests/web_test_helpers";
import { expect, test } from "@odoo/hoot";

class Partner extends models.Model {
    bar = fields.Boolean({ string: "Bar" });
}

defineModels([Partner]);

test("documentation_link: default label and icon", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="bar"/>
            <widget name="documentation_link" path="/this_is_a_test.html"/>
        </form>`,
    });
    expect(".o_doc_link").toHaveText("View Documentation");
    expect(".o_doc_link .fa-external-link").toHaveCount(1);
});

test("documentation_link: given label", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="bar"/>
            <widget name="documentation_link" path="/this_is_a_test.html" label="docdoc"/>
        </form>`,
    });
    expect(".o_doc_link").toHaveText("docdoc");
    expect(".o_doc_link .fa").toHaveCount(0);
});

test("documentation_link: given icon", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="bar"/>
            <widget name="documentation_link" path="/this_is_a_test.html" icon="fa-question-circle"/>
        </form>`,
    });
    expect(".o_doc_link").toHaveText("");
    expect(".o_doc_link .fa-question-circle").toHaveCount(1);
});

test("documentation_link: given label and icon", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="bar"/>
            <widget name="documentation_link" path="/this_is_a_test.html" label="docdoc" icon="fa-question-circle"/>
        </form>`,
    });
    expect(".o_doc_link").toHaveText("docdoc");
    expect(".o_doc_link .fa-question-circle").toHaveCount(1);
});

test("documentation_link: relative path", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="bar"/>
            <widget name="documentation_link" path="/applications/technical/web/settings/this_is_a_test.html"/>
        </form>`,
    });
    expect(".o_doc_link").toHaveAttribute(
        "href",
        "https://www.odoo.com/documentation/1.0/applications/technical/web/settings/this_is_a_test.html"
    );
});

test("documentation_link: absolute path (http)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="bar"/>
                <widget name="documentation_link" path="http://www.odoo.com/"/>
            </form>`,
    });
    expect(".o_doc_link").toHaveAttribute("href", "http://www.odoo.com/");
});

test("documentation_link: absolute path (https)", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
        <form>
            <field name="bar"/>
            <widget name="documentation_link" path="https://www.odoo.com/"/>
        </form>`,
    });

    expect(".o_doc_link").toHaveAttribute("href", "https://www.odoo.com/");
});
