import { expect, getFixture, test } from "@odoo/hoot";
import { queryAllAttributes, queryAllTexts, queryFirst } from "@odoo/hoot-dom";
import {
    contains,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
} from "../../web_test_helpers";

class Product extends models.Model {
    url = fields.Char();
}

defineModels([Product]);

onRpc("has_group", () => true);

test("UrlField in form view", async () => {
    Product._records = [{ id: 1, url: "https://www.example.com" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="url" widget="url"/></form>`,
    });
    expect(`.o_field_widget input[type="text"]`).toHaveCount(1);
    expect(`.o_field_widget input[type="text"]`).toHaveValue("https://www.example.com");
    expect(`.o_field_url a`).toHaveAttribute("href", "https://www.example.com");
    await fieldInput("url").edit("https://www.odoo.com");
    expect(`.o_field_widget input[type="text"]`).toHaveValue("https://www.odoo.com");
});

test("in form view (readonly)", async () => {
    Product._records = [{ id: 1, url: "https://www.example.com" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="url" widget="url" readonly="1"/></form>`,
    });
    expect("a.o_field_widget.o_form_uri").toHaveCount(1);
    expect("a.o_field_widget.o_form_uri").toHaveAttribute("href", "https://www.example.com");
    expect("a.o_field_widget.o_form_uri").toHaveAttribute("target", "_blank");
    expect("a.o_field_widget.o_form_uri").toHaveText("https://www.example.com");
});

test("it takes its text content from the text attribute", async () => {
    Product._records = [{ id: 1, url: "https://www.example.com" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="url" widget="url" text="https://another.com" readonly="1"/></form>',
    });
    expect(`.o_field_url a`).toHaveText("https://another.com");
});

test("href attribute and website_path option", async () => {
    Product._fields.url1 = fields.Char();
    Product._fields.url2 = fields.Char();
    Product._fields.url3 = fields.Char();
    Product._fields.url4 = fields.Char();
    Product._records = [
        {
            id: 1,
            url1: "http://www.url1.com",
            url2: "www.url2.com",
            url3: "http://www.url3.com",
            url4: "https://url4.com",
        },
    ];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `
            <form>
                <field name="url1" widget="url" readonly="1"/>
                <field name="url2" widget="url" readonly="1" options="{'website_path': True}"/>
                <field name="url3" widget="url" readonly="1"/>
                <field name="url4" widget="url" readonly="1"/>
            </form>`,
    });
    expect(`.o_field_widget[name="url1"] a`).toHaveAttribute("href", "http://www.url1.com");
    expect(`.o_field_widget[name="url2"] a`).toHaveAttribute("href", "www.url2.com");
    expect(`.o_field_widget[name="url3"] a`).toHaveAttribute("href", "http://www.url3.com");
    expect(`.o_field_widget[name="url4"] a`).toHaveAttribute("href", "https://url4.com");
});

test("in editable list view", async () => {
    Product._records = [
        { id: 1, url: "example.com" },
        { id: 2, url: "odoo.com" },
    ];
    await mountView({
        type: "list",
        resModel: "product",
        arch: '<list editable="bottom"><field name="url" widget="url"/></list>',
    });
    expect("tbody td:not(.o_list_record_selector) a").toHaveCount(2);
    expect(".o_field_url.o_field_widget[name='url'] a").toHaveCount(2);
    expect(queryAllAttributes(".o_field_url.o_field_widget[name='url'] a", "href")).toEqual([
        "http://example.com",
        "http://odoo.com",
    ]);
    expect(queryAllTexts(".o_field_url.o_field_widget[name='url'] a")).toEqual([
        "example.com",
        "odoo.com",
    ]);
    let cell = queryFirst("tbody td:not(.o_list_record_selector)");
    await contains(cell).click();
    expect(cell.parentElement).toHaveClass("o_selected_row");
    expect(cell.querySelector("input")).toHaveValue("example.com");
    await fieldInput("url").edit("test");
    await contains(getFixture()).click(); // click out
    cell = queryFirst("tbody td:not(.o_list_record_selector)");
    expect(cell.parentElement).not.toHaveClass("o_selected_row");
    expect("tbody td:not(.o_list_record_selector) a").toHaveCount(2);
    expect(".o_field_url.o_field_widget[name='url'] a").toHaveCount(2);
    expect(queryAllAttributes(".o_field_url.o_field_widget[name='url'] a", "href")).toEqual([
        "http://test",
        "http://odoo.com",
    ]);
    expect(queryAllTexts(".o_field_url.o_field_widget[name='url'] a")).toEqual([
        "test",
        "odoo.com",
    ]);
});

test("with falsy value", async () => {
    Product._records = [{ id: 1, url: false }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: '<form><field name="url" widget="url"/></form>',
    });
    expect(`[name=url] input`).toHaveCount(1);
    expect(`[name=url] input`).toHaveValue("");
});

test("onchange scenario", async () => {
    Product._fields.url_source = fields.Char({
        onChange: (record) => (record.url = record.url_source),
    });
    Product._records = [{ id: 1, url: "odoo.com", url_source: "another.com" }];
    await mountView({
        type: "form",
        resModel: "product",
        resId: 1,
        arch: `<form><field name="url" widget="url" readonly="True"/><field name="url_source"/></form>`,
    });
    expect(".o_field_widget[name=url]").toHaveText("odoo.com");
    expect(".o_field_widget[name=url_source] input").toHaveValue("another.com");
    await fieldInput("url_source").edit("example.com");
    expect(".o_field_widget[name=url]").toHaveText("example.com");
});

test("with placeholder", async () => {
    Product._records = [{ id: 1 }];
    await mountView({
        type: "form",
        resModel: "product",
        arch: `<form><field name="url" widget="url" placeholder="Placeholder"/></form>`,
    });
    expect(`.o_field_widget input`).toHaveAttribute("placeholder", "Placeholder");
});

test("with non falsy, but non url value", async () => {
    Product._fields.url.default = "odoo://hello";
    await mountView({
        type: "form",
        resModel: "product",
        arch: `<form><field name="url" widget="url"/></form>`,
    });
    expect(".o_field_widget[name=url] a").toHaveAttribute("href", "http://odoo://hello");
});
