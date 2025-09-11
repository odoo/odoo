import { importRecordsItem } from "@base_import/import_records/import_records";
import { before, expect, test } from "@odoo/hoot";
import { animationFrame, press } from "@odoo/hoot-dom";
import {
    clearRegistry,
    contains,
    defineModels,
    fields,
    mockService,
    models,
    mountView,
    onRpc,
    selectFieldDropdownItem,
    toggleActionMenu,
} from "@web/../tests/web_test_helpers";
import { registry } from "@web/core/registry";

class Foo extends models.Model {
    foo = fields.Char();

    _records = [{ id: 1, foo: "yop" }];
}

defineModels([Foo]);

onRpc("has_group", () => true);

before(() => {
    const cogMenuRegistry = registry.category("cogMenu");
    clearRegistry(cogMenuRegistry);
    cogMenuRegistry.add("import-menu", importRecordsItem);
});

test.tags("desktop");
test(`import in cog menu dropdown in list`, async () => {
    mockService("action", {
        doAction(action, options) {
            expect.step(action.tag);
            expect(action.params.context.foo).toBe("bar");
            return super.doAction(action, options);
        },
    });

    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list><field name="foo"/></list>`,
        config: {
            actionType: "ir.actions.act_window",
        },
        context: {
            foo: "bar",
        },
    });
    await toggleActionMenu();
    expect(`.o-dropdown--menu`).toHaveCount(1);
    expect(`.o_import_menu`).toHaveCount(1);

    await contains(`.o_import_menu`).click();
    expect.verifySteps(["import"]);
});

test(`import should not be available in cog menu dropdown in list with create="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list create="0"><field name="foo"/></list>`,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    expect(`.o_cp_action_menus`).toHaveCount(0);
    expect(`.o_import_menu`).toHaveCount(0);
});

test(`import should not be available in cog menu dropdown in list with import="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list import="0"><field name="foo"/></list>`,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    expect(`.o_cp_action_menus`).toHaveCount(0);
    expect(`.o_import_menu`).toHaveCount(0);
});

test.tags("desktop");
test(`cog menu should open with alt+u shortcut`, async () => {
    await mountView({
        resModel: "foo",
        type: "list",
        arch: `<list/>`,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    await press(["alt", "u"]);
    await animationFrame();
    expect(`.o-dropdown--menu`).toHaveCount(1);
});

test.tags("desktop");
test(`import in cog menu dropdown in kanban`, async () => {
    mockService("action", {
        doAction(action, options) {
            expect.step(action.tag);
            expect(action.params.context.foo).toBe("bar");
            return super.doAction(action, options);
        },
    });

    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        config: {
            actionType: "ir.actions.act_window",
        },
        context: {
            foo: "bar",
        },
    });
    await toggleActionMenu();
    expect(`.o-dropdown--menu`).toHaveCount(1);
    expect(`.o_import_menu`).toHaveCount(1);

    await contains(`.o_import_menu`).click();
    expect.verifySteps(["import"]);
});

test(`import should not be available in cog menu dropdown in kanban with create="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban create="0">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    // Cog menu will not show when empty
    expect(`.o_cp_action_menus`).toHaveCount(0);
});

test(`import should not be available in cog menu dropdown in kanban with import="0"`, async () => {
    await mountView({
        resModel: "foo",
        type: "kanban",
        arch: `
            <kanban import="0">
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    // Cog menu will not show when empty
    expect(`.o_cp_action_menus`).toHaveCount(0);
});

test(`import should not be available in cog menu dropdown in pivot (other than kanban or list)`, async () => {
    Foo._fields.foobar = fields.Integer({ aggregator: "sum" });

    await mountView({
        resModel: "foo",
        type: "pivot",
        arch: `<pivot><field name="foobar" type="measure"/></pivot>`,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    // Cog menu will not show when empty
    expect(`.o_cp_action_menus`).toHaveCount(0);
});

test.tags("desktop");
test(`import should not be available in cog menu dropdown in dialog view`, async () => {
    class Bar extends models.Model {
        name = fields.Char();

        _records = Array.from({ length: 10 }, (_, i) => ({
            id: i + 1,
            name: `Bar ${i + 1}`,
        }));
        _views = {
            list: `<list><field name="display_name"/></list>`,
            search: `<search/>`,
        };
    }
    defineModels([Bar]);

    Foo._fields.m2o = fields.Many2one({ relation: "bar" });

    await mountView({
        resModel: "foo",
        type: "form",
        arch: `<form><field name="m2o"/></form>`,
        config: {
            actionType: "ir.actions.act_window",
        },
    });
    await selectFieldDropdownItem("m2o", "Search more...");
    expect(`.o_dialog .o_cp_action_menus`).toHaveCount(0);
    expect(`.o_dialog .o_import_menu`).toHaveCount(0);
});
