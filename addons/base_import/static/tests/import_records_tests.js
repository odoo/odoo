/** @odoo-module **/

import { importRecordsItem } from "@base_import/import_records/import_records";

import { registry } from "@web/core/registry";

import { click, getFixture, selectDropdownItem } from "@web/../tests/helpers/utils";
import { toggleFavoriteMenu } from "@web/../tests/search/helpers";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

const favoriteMenuRegistry = registry.category("favoriteMenu");

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
        favoriteMenuRegistry.add("import-menu", importRecordsItem);
    });

    QUnit.module("ImportRecords");

    QUnit.test("import in favorite dropdown in list", async function (assert) {
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

        await toggleFavoriteMenu(target);
        assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
        assert.containsOnce(target, ".o_import_menu");
        await click(target.querySelector(".o_import_menu"));
    });

    QUnit.test(
        'import favorite dropdown item should not be in list with create="0"',
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

            await toggleFavoriteMenu(target);
            assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test(
        'import favorite dropdown item should not be in list with import="0"',
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

            await toggleFavoriteMenu(target);
            assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test("import in favorite dropdown in kanban", async function (assert) {
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

        await toggleFavoriteMenu(target);
        assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
        assert.containsOnce(target, ".o_import_menu");
        await click(target.querySelector(".o_import_menu"));
    });

    QUnit.test(
        'import favorite dropdown item should not be in list with create="0"',
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

            await toggleFavoriteMenu(target);
            assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test(
        'import dropdown favorite should not be in kanban with import="0"',
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

            await toggleFavoriteMenu(target);
            assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test(
        "import should not be available in favorite dropdown in pivot (other than kanban or list)",
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

            await toggleFavoriteMenu(target);
            assert.containsOnce(target, ".o_favorite_menu .o-dropdown--menu");
            assert.containsNone(target, ".o_import_menu");
        }
    );

    QUnit.test(
        "import should not be available in favorite dropdown in dialog view",
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
            await toggleFavoriteMenu(dialog);
            assert.containsOnce(dialog, ".o_favorite_menu .o-dropdown--menu");
            assert.containsNone(dialog, ".o_import_menu");
        }
    );
});
