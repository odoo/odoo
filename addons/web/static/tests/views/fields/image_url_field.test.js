import { expect, test } from "@odoo/hoot";
import { click, edit } from "@odoo/hoot-dom";
import { animationFrame, runAllTimers } from "@odoo/hoot-mock";
import {
    defineModels,
    fields,
    models,
    mountView,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { KanbanController } from "@web/views/kanban/kanban_controller";

const FR_FLAG_URL = "/base/static/img/country_flags/fr.png";
const EN_FLAG_URL = "/base/static/img/country_flags/gb.png";

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();
    p = fields.One2many({ relation: "partner" });
    timmy = fields.Many2many({ relation: "partner.type" });

    _records = [{ id: 1, foo: FR_FLAG_URL, timmy: [] }];
}

class PartnerType extends models.Model {
    name = fields.Char();
    color = fields.Integer();

    _records = [
        { id: 12, display_name: "gold", color: 2 },
        { id: 14, display_name: "silver", color: 5 },
    ];
}

class User extends models.Model {
    _name = "res.users";
    has_group() {
        return true;
    }
}

defineModels([Partner, PartnerType, User]);

test("image fields are correctly rendered", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
            </form>
        `,
        resId: 1,
    });

    expect(`div[name="foo"]`).toHaveClass("o_field_image_url", {
        message: "the widget should have the correct class",
    });
    expect(`div[name="foo"] > img`).toHaveCount(1, {
        message: "the widget should contain an image",
    });
    expect(`div[name="foo"] > img`).toHaveAttribute("data-src", FR_FLAG_URL, {
        message: "the image should have the correct src",
    });
    expect(`div[name="foo"] > img`).toHaveClass("img-fluid", {
        message: "the image should have the correct class",
    });
    expect(`div[name="foo"] > img`).toHaveAttribute("width", "90", {
        message: "the image should correctly set its attributes",
    });
    expect(`div[name="foo"] > img`).toHaveStyle("maxWidth: 90px", {
        message: "the image should correctly set its attributes",
    });
});

test("ImageUrlField in subviews are loaded correctly", async () => {
    PartnerType._fields.image = fields.Char();
    PartnerType._records[0].image = EN_FLAG_URL;
    Partner._records[0].timmy = [12];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
                <field name="timmy" widget="many2many" mode="kanban">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="display_name"/>
                            </t>
                        </templates>
                    </kanban>
                    <form>
                        <field name="image" widget="image_url"/>
                    </form>
                </field>
            </form>
        `,
        resId: 1,
    });

    expect(`img[data-src="${FR_FLAG_URL}"]`).toHaveCount(1, {
        message: "The view's image is in the DOM",
    });
    expect(".o_kanban_record:not(.o_kanban_ghost):not(.o-kanban-button-new)").toHaveCount(1, {
        message: "There should be one record in the many2many",
    });

    // Actual flow: click on an element of the m2m to get its form view
    await click(".o_kanban_record:not(.o_kanban_ghost):not(.o-kanban-button-new)");
    await animationFrame();
    expect(".modal").toHaveCount(1, { message: "The modal should have opened" });
    expect(`img[data-src="${EN_FLAG_URL}"]`).toHaveCount(1, {
        message: "The dialog's image is in the DOM",
    });
});

test("image fields in x2many list are loaded correctly", async () => {
    PartnerType._fields.image = fields.Char();
    PartnerType._records[0].image = EN_FLAG_URL;
    Partner._records[0].timmy = [12];

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="timmy" widget="many2many">
                    <list>
                        <field name="image" widget="image_url"/>
                    </list>
                </field>
            </form>
        `,
        resId: 1,
    });

    expect("tr.o_data_row").toHaveCount(1, {
        message: "There should be one record in the many2many",
    });
    expect(`img[data-src="${EN_FLAG_URL}"]`).toHaveCount(1, {
        message: "The list's image is in the DOM",
    });
});

test("image url fields in kanban don't stop opening record", async () => {
    patchWithCleanup(KanbanController.prototype, {
        openRecord() {
            expect.step("open record");
        },
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo" widget="image_url"/>
                    </t>
                </templates>
            </kanban>
        `,
    });

    await click(".o_kanban_record");
    await animationFrame();
    expect.verifySteps(["open record"]);
});

test("image fields with empty value", async () => {
    Partner._records[0].foo = false;

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
            </form>
        `,
        resId: 1,
    });

    expect(`div[name="foo"]`).toHaveClass("o_field_image_url", {
        message: "the widget should have the correct class",
    });
    expect(`div[name="foo"] > img`).toHaveCount(0, {
        message: "the widget should not contain an image",
    });
});

test("onchange update image fields", async () => {
    const srcTest = "/my/test/src";
    Partner._onChanges.name = (record) => {
        record.foo = srcTest;
    };

    await mountView({
        type: "form",
        resModel: "partner",
        arch: /* xml */ `
            <form>
                <field name="name"/>
                <field name="foo" widget="image_url" options="{'size': [90, 90]}"/>
            </form>
        `,
        resId: 1,
    });

    expect(`div[name="foo"] > img`).toHaveAttribute("data-src", FR_FLAG_URL, {
        message: "the image should have the correct src",
    });

    await click(`[name="name"] input`);
    await edit("test", { confirm: "enter" });
    await runAllTimers();
    await animationFrame();
    expect(`div[name="foo"] > img`).toHaveAttribute("data-src", srcTest, {
        message: "the image should have the onchange src",
    });
});
