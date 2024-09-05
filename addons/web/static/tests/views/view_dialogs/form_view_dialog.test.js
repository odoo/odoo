import { expect, test } from "@odoo/hoot";
import { click, edit, press, queryAllTexts } from "@odoo/hoot-dom";
import { animationFrame, Deferred } from "@odoo/hoot-mock";
import {
    clickSave,
    defineModels,
    fields,
    getService,
    models,
    mountViewInDialog,
    mountWithCleanup,
    onRpc,
    mockService,
    fieldInput,
} from "@web/../tests/web_test_helpers";

import { FormViewDialog } from "@web/views/view_dialogs/form_view_dialog";
import { WebClient } from "@web/webclient/webclient";

class Partner extends models.Model {
    name = fields.Char({ string: "Displayed name" });
    foo = fields.Char({ string: "Foo" });
    bar = fields.Boolean({ string: "Bar" });
    instrument = fields.Many2one({
        string: "Instruments",
        relation: "instrument",
    });
    method1() {}
    method2() {}
    _records = [
        { id: 1, foo: "blip", name: "blipblip", bar: true },
        { id: 2, foo: "ta tata ta ta", name: "macgyver", bar: false },
        { id: 3, foo: "piou piou", name: "Jack O'Neill", bar: true },
    ];
}

class Instrument extends models.Model {
    name = fields.Char({ string: "name" });
    badassery = fields.Many2many({
        string: "level",
        relation: "badassery",
        domain: [["level", "=", "Awsome"]],
    });
}

class Badassery extends models.Model {
    level = fields.Char({ string: "level" });

    _records = [{ id: 1, level: "Awsome" }];
}

class Product extends models.Model {
    name = fields.Char({ string: "name" });
    partner = fields.One2many({ string: "Doors", relation: "partner" });

    _records = [{ id: 1, name: "The end" }];
}

defineModels([Partner, Instrument, Badassery, Product]);

test("formviewdialog buttons in footer are positioned properly", async () => {
    Partner._views["form,false"] = /* xml */ `
        <form string="Partner">
            <sheet>
                <group><field name="foo"/></group >
                <footer><button string="Custom Button" type="object" class="btn-primary"/></footer>
            </sheet>
        </form>
    `;

    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });

    await animationFrame();

    expect(".modal-body button").toHaveCount(0, { message: "should not have any button in body" });
    expect(".modal-footer button:not(.d-none)").toHaveCount(1, {
        message: "should have only one button in footer",
    });
});

test("modifiers are considered on multiple <footer/> tags", async () => {
    Partner._views["form,false"] = /* xml */ `
        <form>
            <field name="bar"/>
            <footer invisible="not bar">
                <button>Hello</button>
                <button>World</button>
            </footer>
            <footer invisible="bar">
                <button>Foo</button>
            </footer>
        </form>
    `;
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });

    await animationFrame();

    expect(queryAllTexts(".modal-footer button:not(.d-none)")).toEqual(["Hello", "World"], {
        message: "only the first button section should be visible",
    });

    await click(".o_field_boolean input");
    await animationFrame();
    expect(queryAllTexts(".modal-footer button:not(.d-none)")).toEqual(["Foo"], {
        message: "only the second button section should be visible",
    });
});

test("formviewdialog buttons in footer are not duplicated", async () => {
    Partner._fields.poney_ids = fields.One2many({
        string: "Poneys",
        relation: "partner",
    });
    Partner._records[0].poney_ids = [];
    Partner._views["form,false"] = /* xml */ `
        <form string="Partner">
            <field name="poney_ids"><list editable="top"><field name="name"/></list></field>
            <footer><button string="Custom Button" type="object" class="my_button"/></footer>
        </form>
    `;
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });
    await animationFrame();

    expect(".modal").toHaveCount(1);
    expect(".modal button.my_button").toHaveCount(1, { message: "should have 1 buttons in modal" });

    await click(".o_field_x2many_list_row_add a");
    await animationFrame();
    await press("escape");
    await animationFrame();

    expect(".modal").toHaveCount(1);
    expect(".modal button.btn-primary").toHaveCount(1, {
        message: "should still have 1 buttons in modal",
    });
});

test.tags("desktop")("Form dialog and subview with _view_ref contexts", async () => {
    expect.assertions(2);

    Instrument._records = [{ id: 1, name: "Tromblon", badassery: [1] }];
    Partner._records[0].instrument = 1;
    // This is an old test, written before "get_views" (formerly "load_views") automatically
    // inlines x2many subviews. As the purpose of this test is to assert that the js fetches
    // the correct sub view when it is not inline (which can still happen in nested form views),
    // we bypass the inline mecanism of "get_views" by setting widget="many2many" on the field.
    Instrument._views["form,false"] = /* xml */ `
        <form>
            <field name="name"/>
            <field name="badassery" widget="many2many" context="{'list_view_ref': 'some_other_tree_view'}"/>
        </form>
    `;
    Badassery._views["list,false"] = /* xml */ `<list><field name="level"/></list>`;

    onRpc(({ kwargs, method, model }) => {
        if (method === "get_formview_id") {
            return false;
        }
        if (method === "get_views" && model === "instrument") {
            expect(kwargs.context).toEqual(
                {
                    allowed_company_ids: [1],
                    lang: "en",
                    list_view_ref: "some_tree_view",
                    tz: "taht",
                    uid: 7,
                },
                {
                    message:
                        "1 The correct _view_ref should have been sent to the server, first time",
                }
            );
        }
        if (method === "get_views" && model === "badassery") {
            expect(kwargs.context).toEqual(
                {
                    allowed_company_ids: [1],
                    lang: "en",
                    list_view_ref: "some_other_tree_view",
                    tz: "taht",
                    uid: 7,
                },
                {
                    message:
                        "2 The correct _view_ref should have been sent to the server for the subview",
                }
            );
        }
    });

    await mountViewInDialog({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="instrument" context="{'list_view_ref': 'some_tree_view'}"/>
            </form>
        `,
    });
    await click('.o_field_widget[name="instrument"] button.o_external_button');
    await animationFrame();
});

test("click on view buttons in a FormViewDialog", async () => {
    Partner._views["form,false"] = /* xml */ `
        <form>
            <field name="foo"/>
            <button name="method1" type="object" string="Button 1" class="btn1"/>
            <button name="method2" type="object" string="Button 2" class="btn2" close="1"/>
        </form>
    `;

    onRpc(({ method }) => expect.step(method));

    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .o_form_view button").toHaveCount(2);
    expect.verifySteps(["get_views", "web_read"]);
    await click(".o_dialog .o_form_view .btn1");
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect.verifySteps(["method1", "web_read"]); // should re-read the record
    await click(".o_dialog .o_form_view .btn2");
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(0);
    expect.verifySteps(["method2"]); // should not read as we closed
});

test("formviewdialog is not closed when button handlers return a rejected promise", async () => {
    expect.errors(1);
    Partner._views["form,false"] = /* xml */ `
        <form string="Partner">
            <sheet><group><field name="foo"/></group></sheet>
        </form>
    `;
    let reject = true;
    onRpc("web_save", async () => {
        if (reject) {
            return Promise.reject();
        }
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        context: { answer: 42 },
    });

    await animationFrame();
    expect(".modal-body button").toHaveCount(0, { message: "should not have any button in body" });
    expect(".modal-footer button").toHaveCount(3, { message: "should have 3 buttons in footer" });

    // clickSave inside the dialog
    await clickSave({ index: 1 });

    expect(".modal").toHaveCount(2, {
        message: "there are 2 modal opened, 1 for the error and 1 for the form view dialog",
    });
    await click(".o_error_dialog .btn-primary");
    await animationFrame();

    expect(".modal").toHaveCount(1, { message: "modal should still be opened" });

    reject = false;
    // clickSave inside the dialog
    await clickSave({ index: 1 });
    expect(".modal").toHaveCount(0, { message: "modal should be closed" });
});

test("FormViewDialog with remove button", async () => {
    Partner._views["form,false"] = /* xml */ `<form><field name="foo"/></form>`;
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
        removeRecord: () => expect.step("remove"),
    });
    await animationFrame();

    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-footer .o_form_button_remove").toHaveCount(1);
    await click(".o_dialog .modal-footer .o_form_button_remove");
    await animationFrame();
    expect.verifySteps(["remove"]);
    expect(".o_dialog .o_form_view").toHaveCount(0);
});

test("Buttons are set as disabled on click", async () => {
    Partner._views["form,false"] = /* xml */ `
        <form string="Partner">
            <sheet>
                <group>
                    <field name="name"/>
                </group>
            </sheet>
        </form>
    `;

    const def = new Deferred();
    onRpc("web_save", async () => await def);
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });

    await animationFrame();

    await click(".o_dialog .o_content .o_field_char .o_input");
    await edit("test");
    await animationFrame();

    await clickSave();

    expect(".o_dialog .modal-footer .o_form_button_save").toHaveAttribute("disabled", "1");

    def.resolve();
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(0);
});

test("FormViewDialog with discard button", async () => {
    Partner._views["form,false"] = /* xml */ `<form><field name="foo"/></form>`;
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
        onRecordDiscarded: () => expect.step("discard"),
    });
    await animationFrame();

    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-footer .o_form_button_cancel").toHaveCount(1);
    await click(".o_dialog .modal-footer .o_form_button_cancel");
    await animationFrame();
    expect.verifySteps(["discard"]);
    expect(".o_dialog .o_form_view").toHaveCount(0);
});

test("Save a FormViewDialog when a required field is empty don't close the dialog", async () => {
    Partner._views["form,false"] = /* xml */ `
        <form string="Partner">
            <sheet>
                <group><field name="foo" required="1"/></group>
            </sheet>
            <footer>
                <button name="save" special="save" class="btn-primary"/>
            </footer>
        </form>
    `;
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        context: { answer: 42 },
    });

    await animationFrame();

    await click('.modal button[name="save"]');
    await animationFrame();

    expect(".modal").toHaveCount(1, { message: "modal should still be opened" });
    await click("[name='foo'] input");
    await edit("new");
    await click('.modal button[name="save"]');
    await animationFrame();
    expect(".modal").toHaveCount(0, { message: "modal should be closed" });
});

test.tags("desktop")("new record has an expand button", async () => {
    Partner._views["form,false"] = /* xml */ `<form><field name="foo"/></form>`;
    Partner._records = [];
    onRpc("web_save", async () => {
        expect.step("save");
    });
    mockService("action", {
        doAction(actionRequest) {
            expect.step([
                actionRequest.res_id,
                actionRequest.res_model,
                actionRequest.type,
                actionRequest.views,
            ]);
        },
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
    });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(1);
    await fieldInput("foo").edit("new");
    await click(".o_dialog .modal-header .o_expand_button");
    await animationFrame();
    expect.verifySteps(["save", [1, "partner", "ir.actions.act_window", [[false, "form"]]]]);
});

test.tags("desktop")("existing record has an expand button", async () => {
    Partner._views["form,false"] = /* xml */ `<form><field name="foo"/></form>`;
    onRpc("web_save", async () => {
        expect.step("save");
    });
    mockService("action", {
        doAction(actionRequest) {
            expect.step([
                actionRequest.res_id,
                actionRequest.res_model,
                actionRequest.type,
                actionRequest.views,
            ]);
        },
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(1);
    await fieldInput("foo").edit("hola");
    await click(".o_dialog .modal-header .o_expand_button");
    await animationFrame();
    expect.verifySteps(["save", [1, "partner", "ir.actions.act_window", [[false, "form"]]]]);
});

test.tags("mobile")("no expand button on mobile", async () => {
    Partner._views["form,false"] = /* xml */ `<form><field name="foo"/></form>`;
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "partner",
        resId: 1,
    });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(0);
});

test.tags("desktop")("expand button with save and new", async () => {
    Instrument._views["form,false"] = /* xml */ `<form><field name="name"/></form>`;
    Instrument._records = [{ id: 1, name: "Violon" }];
    onRpc("web_save", async () => {
        expect.step("save");
    });
    mockService("action", {
        doAction(actionRequest) {
            expect.step([
                actionRequest.res_id,
                actionRequest.res_model,
                actionRequest.type,
                actionRequest.views,
            ]);
        },
    });
    await mountWithCleanup(WebClient);
    getService("dialog").add(FormViewDialog, {
        resModel: "instrument",
        resId: 1,
        isToMany: true,
    });
    await animationFrame();
    expect(".o_dialog .o_form_view").toHaveCount(1);
    expect(".o_dialog .modal-header .o_expand_button").toHaveCount(1);
    await fieldInput("name").edit("Violoncelle");
    await click(".o_dialog .modal-footer .o_form_button_save_new");
    await animationFrame();
    await fieldInput("name").edit("Flute");
    await click(".o_dialog .modal-header .o_expand_button");
    await animationFrame();
    expect.verifySteps([
        "save",
        "save",
        [2, "instrument", "ir.actions.act_window", [[false, "form"]]],
    ]);
});
