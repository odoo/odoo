import { expect, test } from "@odoo/hoot";
import { runAllTimers } from "@odoo/hoot-mock";
import {
    clickFieldDropdown,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    MockServer,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

import "@hr_work_entry/components/work_entry_type_field/work_entry_type_field";

class HrWorkEntryType extends models.Model {
    _name = "hr.work.entry.type";
    name = fields.Char();
    display_code = fields.Char();
    color = fields.Integer();
    _records = [
        { id: 10, name: "Attendance", display_code: "A", color: 2 },
        { id: 20, name: "Time Off", display_code: "T", color: 5 },
    ];
}

class HrWorkEntry extends models.Model {
    _name = "hr.work.entry";
    name = fields.Char();
    work_entry_type_id = fields.Many2one({ relation: "hr.work.entry.type" });
    display_code = fields.Char();
    color = fields.Integer();
    _records = [{ id: 1, name: "Entry 1", work_entry_type_id: 10, display_code: "A", color: 2 }];

    _onChanges = {
        work_entry_type_id(record) {
            const id = Array.isArray(record.work_entry_type_id)
                ? record.work_entry_type_id[0]
                : record.work_entry_type_id;
            const type = MockServer.env["hr.work.entry.type"].find((r) => r.id === id);
            record.display_code = type ? type.display_code : false;
            record.color = type ? type.color : false;
        },
    };
}

defineMailModels();
defineModels([HrWorkEntryType, HrWorkEntry]);

const FORM_ARCH = `
    <form>
        <field name="work_entry_type_id" widget="many2one_work_entry_type"/>
    </form>`;

const AVATAR = ".o_field_widget[name=work_entry_type_id] .o_calendar_renderer span";

test.tags("desktop");
test("dropdown selection shows display_code and color", async () => {
    await mountView({
        type: "form",
        resModel: "hr.work.entry",
        resId: 1,
        arch: FORM_ARCH,
    });

    expect(AVATAR).toHaveText("A");
    expect(AVATAR).toHaveClass("o_calendar_color_2");

    await clickFieldDropdown("work_entry_type_id");
    await contains(
        ".o_field_widget[name=work_entry_type_id] .dropdown-menu li:contains('Time Off')"
    ).click();

    expect(AVATAR).toHaveText("T");
    expect(AVATAR).toHaveClass("o_calendar_color_5");
});

test.tags("desktop");
test("search more selection refetches display_code and color", async () => {
    for (let i = 0; i < 10; i++) {
        HrWorkEntryType._records.push({
            id: 100 + i,
            name: `Type ${i}`,
            display_code: `X${i}`,
            color: 1,
        });
    }
    HrWorkEntryType._records.push({ id: 200, name: "Special", display_code: "S", color: 7 });
    HrWorkEntryType._views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
    };

    onRpc("hr.work.entry.type", "read", ({ args }) => {
        expect.step(`read:${args[0].join(",")}:${args[1].join(",")}`);
    });

    await mountView({
        type: "form",
        resModel: "hr.work.entry",
        resId: 1,
        arch: FORM_ARCH,
    });

    await contains(`.o_field_widget[name=work_entry_type_id] input`).click();
    await runAllTimers();
    await contains(
        `.o_field_widget[name=work_entry_type_id] .o_m2o_dropdown_option_search_more`
    ).click();
    await contains(".modal .o_data_row .o_data_cell:contains('Special')").click();

    expect.verifySteps(["read:200:display_name,display_code,color"]);
    expect(AVATAR).toHaveText("S");
    expect(AVATAR).toHaveClass("o_calendar_color_7");
});

test.tags("desktop");
test("search more 'Create New' refetches display_code and color of the new record", async () => {
    HrWorkEntryType._views = {
        list: `<list><field name="name"/></list>`,
        search: `<search/>`,
        form: `<form>
            <field name="name"/>
            <field name="display_code"/>
            <field name="color"/>
        </form>`,
    };

    onRpc("hr.work.entry.type", "web_save", () => {
        expect.step("web_save");
    });
    onRpc("hr.work.entry.type", "read", ({ args }) => {
        expect.step(`read:${args[1].join(",")}`);
    });

    await mountView({
        type: "form",
        resModel: "hr.work.entry",
        resId: 1,
        arch: FORM_ARCH,
    });

    await contains(`.o_field_widget[name=work_entry_type_id] input`).click();
    await runAllTimers();
    await contains(
        `.o_field_widget[name=work_entry_type_id] .o_m2o_dropdown_option_search_more`
    ).click();

    await contains(".modal .o_create_button").click();

    await contains(".modal .o_field_widget[name=name] input").edit("New Type");
    await contains(".modal .o_field_widget[name=display_code] input").edit("N");
    await contains(".modal .o_field_widget[name=color] input").edit("3");
    await contains(".modal .o_form_button_save").click();

    expect.verifySteps(["web_save", "read:display_name,display_code,color"]);
    expect(AVATAR).toHaveText("N");
    expect(AVATAR).toHaveClass("o_calendar_color_3");
});
