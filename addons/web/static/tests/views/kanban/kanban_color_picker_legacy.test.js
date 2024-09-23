import { beforeEach, expect, test } from "@odoo/hoot";
import { KanbanArchParser } from "@web/views/kanban/kanban_arch_parser";
import { parseXML } from "@web/core/utils/xml";
import {
    contains,
    defineModels,
    fields,
    getDropdownMenu,
    getKanbanRecord,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    toggleKanbanRecordDropdown,
} from "../../web_test_helpers";
import { queryAll } from "@odoo/hoot-dom";

function parseArch(arch) {
    const parser = new KanbanArchParser();
    const xmlDoc = parseXML(arch);
    return parser.parse(xmlDoc, { fake: { name: { string: "Name", type: "char" } } }, "fake");
}

class Category extends models.Model {
    _name = "category";

    name = fields.Char();
    color = fields.Integer();

    _records = [
        { id: 6, name: "gold", color: 2 },
        { id: 7, name: "silver", color: 5 },
    ];
}

defineModels([Category]);

// avoid "kanban-box" deprecation warnings in this suite, which defines legacy kanban on purpose
beforeEach(() => {
    const originalConsoleWarn = console.warn;
    patchWithCleanup(console, {
        warn: (msg) => {
            if (msg !== "'kanban-box' is deprecated, use 'kanban-card' API instead") {
                originalConsoleWarn(msg);
            }
        },
    });
});

test("oe_kanban_colorpicker in kanban-menu and kanban-box", async () => {
    const archInfo = parseArch(`
        <kanban>
            <templates>
                <t t-name="kanban-menu">
                    <ul class="oe_kanban_colorpicker" data-field="kanban_menu_colorpicker" role="menu"/>
                </t>
                <t t-name="kanban-box"/>
            </templates>
        </kanban>
    `);
    expect(archInfo.colorField).toBe("kanban_menu_colorpicker", {
        message: "colorField should be 'kanban_menu_colorpicker'",
    });

    const archInfo_1 = parseArch(`
        <kanban>
            <templates>
                <t t-name="kanban-menu"/>
                <t t-name="kanban-box">
                    <ul class="oe_kanban_colorpicker" data-field="kanban_box_color" role="menu"/>
                </t>
            </templates>
        </kanban>
    `);
    expect(archInfo_1.colorField).toBe("kanban_box_color", {
        message: "colorField should be 'kanban_box_color'",
    });
});

test("kanban with colorpicker and node with color attribute", async () => {
    Category._fields.colorpickerField = fields.Integer();
    Category._records[0].colorpickerField = 3;

    onRpc("web_save", ({ args }) => {
        expect.step(`write-color-${args[1].colorpickerField}`);
    });

    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban>
                <field name="colorpickerField"/>
                <templates>
                    <t t-name="kanban-menu">
                        <div class="oe_kanban_colorpicker" data-field="colorpickerField"/>
                    </t>
                    <t t-name="kanban-box">
                        <div color="colorpickerField">
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_3");
    await toggleKanbanRecordDropdown(0);
    await contains(`.oe_kanban_colorpicker li[title="Raspberry"] a.oe_kanban_color_9`).click();
    // should write on the color field
    expect.verifySteps(["write-color-9"]);
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_9");
});

test("edit the kanban color with the colorpicker", async () => {
    Category._records[0].color = 12;

    onRpc("web_save", ({ args }) => {
        expect.step(`write-color-${args[1].color}`);
    });

    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban>
                <field name="color"/>
                <templates>
                    <t t-name="kanban-menu">
                        <div class="oe_kanban_colorpicker"/>
                    </t>
                    <t t-name="kanban-box">
                        <div color="color">
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);

    expect(".o_kanban_record.oe_kanban_color_12").toHaveCount(0, {
        message: "no record should have the color 12",
    });
    expect(
        queryAll(".oe_kanban_colorpicker", { root: getDropdownMenu(getKanbanRecord({ index: 0 })) })
    ).toHaveCount(1);
    expect(
        queryAll(".oe_kanban_colorpicker > *", {
            root: getDropdownMenu(getKanbanRecord({ index: 0 })),
        })
    ).toHaveCount(12, { message: "the color picker should have 12 children (the colors)" });

    await contains(".oe_kanban_colorpicker a.oe_kanban_color_9").click();

    // should write on the color field
    expect.verifySteps(["write-color-9"]);
    expect(getKanbanRecord({ index: 0 })).toHaveClass("o_kanban_color_9");
});

test("colorpicker doesn't appear when missing access rights", async () => {
    await mountView({
        type: "kanban",
        resModel: "category",
        arch: `
            <kanban edit="0">
                <field name="color"/>
                <templates>
                    <t t-name="kanban-menu">
                        <div class="oe_kanban_colorpicker"/>
                    </t>
                    <t t-name="kanban-box">
                        <div color="color">
                            <field name="name"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
    });

    await toggleKanbanRecordDropdown(0);

    expect(".oe_kanban_colorpicker").toHaveCount(0, {
        message: "there shouldn't be a color picker",
    });
});
