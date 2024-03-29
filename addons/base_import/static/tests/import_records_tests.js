/** @odoo-module **/

import { importRecordsItem } from "@base_import/import_records/import_records";

import { registry } from "@web/core/registry";

import { click, getFixture, selectDropdownItem, triggerHotkey } from "@web/../tests/helpers/utils";
import { toggleActionMenu } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { clearRegistryWithCleanup } from "@web/../tests/helpers/mock_env";

let serverData;
let target;

QUnit.module("Base Import Tests", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                    },
                    records: [{ id: 1, foo: "yop" }],
                },
            },
        };
        setupViewRegistries();
        const cogMenuRegistry = registry.category("cogMenu");
        clearRegistryWithCleanup(cogMenuRegistry);
        cogMenuRegistry.add("import-menu", importRecordsItem);
    });

    QUnit.module("ImportRecords");

    QUnit.test("import in cog menu dropdown in list", async function (assert) {
        assert.expect(3);

        const actionService = {
            start() {
                return {
                    doAction: (action, options) => {
                        assert.strictEqual(action.tag, "import");
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree><field name="foo"/></tree>',
            config: {
                actionType: "ir.actions.act_window",
            },
        });

        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus .o-dropdown--menu");
        assert.containsOnce(target, ".o_import_menu");
        await click(target.querySelector(".o_import_menu"));
    });

    QUnit.test(
        'import should not be available in cog menu dropdown in list with create="0"',
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree create="0"><field name="foo"/></tree>',
                config: {
                    actionType: "ir.actions.act_window",
                },
            });

            assert.containsNone(target, ".o_cp_action_menus");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test(
        'import should not be available in cog menu dropdown in list with import="0"',
        async function (assert) {
            await makeView({
                type: "list",
                resModel: "foo",
                serverData,
                arch: '<tree import="0"><field name="foo"/></tree>',
                config: {
                    actionType: "ir.actions.act_window",
                },
            });

            assert.containsNone(target, ".o_cp_action_menus");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test("cog menu should open with alt+u shortcut", async function (assert) {
        await makeView({
            type: "list",
            resModel: "foo",
            serverData,
            arch: '<tree/>',
            config: {
                actionType: "ir.actions.act_window",
            },
        });
        await triggerHotkey("alt+u");
        assert.containsOnce(target, ".o_cp_action_menus .o-dropdown--menu");
    });

    QUnit.test("import in cog menu dropdown in kanban", async function (assert) {
        assert.expect(3);

        const actionService = {
            start() {
                return {
                    doAction: (action, options) => {
                        assert.strictEqual(action.tag, "import");
                    },
                };
            },
        };
        registry.category("services").add("action", actionService, { force: true });

        await makeView({
            type: "kanban",
            resModel: "foo",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div><field name="foo"/></div>
                        </t>
                    </templates>
                </kanban>`,
            config: {
                actionType: "ir.actions.act_window",
            },
        });

        await toggleActionMenu(target);
        assert.containsOnce(target, ".o_cp_action_menus .o-dropdown--menu");
        assert.containsOnce(target, ".o_import_menu");
        await click(target.querySelector(".o_import_menu"));
    });

    QUnit.test(
        'import should not be available in cog menu dropdown in kanban with create="0"',
        async function (assert) {
            await makeView({
                type: "kanban",
                resModel: "foo",
                serverData,
                arch: `
                    <kanban create="0">
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="foo"/></div>
                            </t>
                        </templates>
                    </kanban>`,
                config: {
                    actionType: "ir.actions.act_window",
                },
            });
            // Cog menu will not show when empty
            assert.containsNone(target, ".o_cp_action_menus");
        }
    );

    QUnit.test(
        'import should not be available in cog menu dropdown in kanban with import="0"',
        async function (assert) {
            await makeView({
                type: "kanban",
                resModel: "foo",
                serverData,
                arch: `
                    <kanban import="0">
                        <templates>
                            <t t-name="kanban-box">
                                <div><field name="foo"/></div>
                            </t>
                        </templates>
                    </kanban>`,
                config: {
                    actionType: "ir.actions.act_window",
                },
            });
            // Cog menu will not show when empty
            assert.containsNone(target, ".o_cp_action_menus");
        }
    );

    QUnit.test(
        "import should not be available in cog menu dropdown in pivot (other than kanban or list)",
        async function (assert) {
            serverData.models.foo.fields.foobar = {
                string: "Fubar",
                type: "integer",
                group_operator: "sum",
            };

            await makeView({
                type: "pivot",
                resModel: "foo",
                serverData,
                arch: '<pivot><field name="foobar" type="measure"/></pivot>',
                config: {
                    actionType: "ir.actions.act_window",
                },
            });
            // Cog menu will not show when empty
            assert.containsNone(target, ".o_cp_action_menus");
        }
    );

    QUnit.test(
        "import should not be available in cog menu dropdown in dialog view",
        async function (assert) {
            serverData.models.bar = {
                fields: {
                    display_name: { string: "Bar", type: "char" },
                },
                records: [],
            };
            for (let i = 0; i < 10; i++) {
                serverData.models.bar.records.push({ id: i + 1, display_name: "Bar " + (i + 1) });
            }
            serverData.models.foo.fields.m2o = { string: "M2O", type: "many2one", relation: "bar" };

            serverData.views = {
                "bar,false,list": '<tree><field name="display_name"/></tree>',
                "bar,false,search": "<search></search>",
            };
            await makeView({
                type: "form",
                resModel: "foo",
                serverData,
                arch: '<form><field name="m2o"/></form>',
                config: {
                    actionType: "ir.actions.act_window",
                },
            });

            await selectDropdownItem(target, "m2o", "Search More...");
            const dialog = target.querySelector(".modal");
            assert.containsNone(dialog, ".o_cp_action_menus");
            assert.containsNone(dialog, ".o_import_menu");
        }
    );
});
