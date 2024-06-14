/* global ace */

import { expect, getFixture, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

import {
    clickSave,
    contains,
    defineModels,
    editAce,
    fields,
    models,
    mountView,
    onRpc,
    pagerNext,
    preventResizeObserverError,
} from "@web/../tests/web_test_helpers";

class Partner extends models.Model {
    _name = "res.partner";
    _rec_name = "display_name";

    foo = fields.Text({ string: "Foo", searchable: true, default: "My little Foo Value" });

    _records = [
        { id: 1, foo: "yop" },
        { id: 2, foo: "blip" },
    ];
}

defineModels([Partner]);

preventResizeObserverError();

test("AceEditorField on text fields works", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="foo" widget="code"/></form>`,
    });
    expect("ace" in window).toBe(true, { message: "the ace library should be loaded" });
    expect(`div.ace_content`).toHaveCount(1);
    expect(".o_field_code").toHaveText(/yop/);
});

test("AceEditorField mark as dirty as soon at onchange", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="foo" widget="code"/></form>`,
    });

    const aceEditor = queryOne`.ace_editor`;
    expect(aceEditor).toHaveText(/yop/);

    // edit the foo field
    ace.edit(aceEditor).setValue("blip");
    await animationFrame();
    expect(`.o_form_status_indicator_buttons`).toHaveCount(1);
    expect(`.o_form_status_indicator_buttons`).not.toHaveClass("invisible");

    // revert edition
    ace.edit(aceEditor).setValue("yop");
    await animationFrame();
    expect(`.o_form_status_indicator_buttons`).toHaveCount(1);
    expect(`.o_form_status_indicator_buttons`).toHaveClass("invisible");
});

test("AceEditorField on html fields works", async () => {
    Partner._fields.html_field = fields.Html();
    Partner._records.push({ id: 3, html_field: `<p>My little HTML Test</p>` });

    onRpc(({ method }) => expect.step(method));

    await mountView({
        resModel: "res.partner",
        resId: 3,
        type: "form",
        arch: `<form><field name="html_field" widget="code" /></form>`,
    });
    expect(".o_field_code").toHaveText(/My little HTML Test/);
    expect(["get_views", "web_read"]).toVerifySteps();

    // Modify foo and save
    await editAce("DEF");
    await clickSave();
    expect(["web_save"]).toVerifySteps();
});

test.tags`desktop`("AceEditorField doesn't crash when editing", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        type: "form",
        arch: `<form><field name="foo" widget="code"/></form>`,
    });

    await contains(".ace_editor .ace_content").click();
    expect(".ace-view-editor").toHaveClass("ace_focus");
});

test("AceEditorField is updated on value change", async () => {
    await mountView({
        resModel: "res.partner",
        resId: 1,
        resIds: [1, 2],
        type: "form",
        arch: `<form><field name="foo" widget="code"/></form>`,
    });
    expect(".o_field_code").toHaveText(/yop/);

    await pagerNext();
    await animationFrame();
    await animationFrame();
    expect(".o_field_code").toHaveText(/blip/);
});

test("leaving an untouched record with an unset ace field should not write", async () => {
    for (const record of Partner._records) {
        record.foo = false;
    }

    onRpc(({ args, method }) => {
        if (method) {
            expect.step(`${method}: ${JSON.stringify(args)}`);
        }
    });

    await mountView({
        resModel: "res.partner",
        resId: 1,
        resIds: [1, 2],
        type: "form",
        arch: `<form><field name="foo" widget="code"/></form>`,
    });
    expect(["get_views: []", "web_read: [[1]]"]).toVerifySteps();

    await pagerNext();
    expect(["web_read: [[2]]"]).toVerifySteps();
});

test("AceEditorField only trigger onchanges when blurred", async () => {
    Partner._fields.foo = fields.Text({ onChange: () => {} });
    for (const record of Partner._records) {
        record.foo = false;
    }

    onRpc(({ args, method }) => {
        expect.step(`${method}: ${JSON.stringify(args)}`);
    });

    await mountView({
        resModel: "res.partner",
        resId: 1,
        resIds: [1, 2],
        type: "form",
        arch: `<form><field name="display_name"/><field name="foo" widget="code"/></form>`,
    });
    expect(["get_views: []", "web_read: [[1]]"]).toVerifySteps();

    await editAce("a");
    await contains(getFixture()).focus(); // blur ace editor
    expect([`onchange: [[1],{"foo":"a"},["foo"],{"display_name":{},"foo":{}}]`]).toVerifySteps();

    await clickSave();
    expect([`web_save: [[1],{"foo":"a"}]`]).toVerifySteps();
});
