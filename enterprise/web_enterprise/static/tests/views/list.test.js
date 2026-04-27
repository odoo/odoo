import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, queryAll } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import {
    contains,
    defineModels,
    fields,
    getDropdownMenu,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { user } from "@web/core/user";
import { WebClientEnterprise } from "@web_enterprise/webclient/webclient";

class Foo extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();

    _records = [
        { id: 1, bar: true, foo: "yop" },
        { id: 2, bar: true, foo: "blip" },
        { id: 3, bar: true, foo: "gnap" },
        { id: 4, bar: false, foo: "blip" },
    ];
}

defineModels([Foo]);

const getDefaultConfig = () => ({
    actionId: 1,
    actionType: "ir.actions.act_window",
});

describe.current.tags("desktop");

beforeEach(() => {
    onRpc("has_group", () => true);
});

test("add custom field button with other optional columns - studio not installed", async () => {
    expect.assertions(8);

    onRpc("search_read", ({ model }) => {
        if (model === "ir.module.module") {
            expect.step("studio_module_id");
            return [{ id: 42 }];
        }
    });
    onRpc("button_immediate_install", ({ model, args }) => {
        if (model === "ir.module.module") {
            expect(args[0]).toEqual([42], {
                message: "Should be the id of studio module returned by the search read",
            });
            expect.step("studio_module_install");
            return true;
        }
    });
    await mountView({
        type: "list",
        resModel: "foo",
        arch: /* xml */ `
            <list>
                <field name="foo"/>
                <field name="bar" optional="hide"/>
            </list>
        `,
        config: getDefaultConfig(),
    });

    patchWithCleanup(browser.location, {
        reload: function () {
            expect.step("window_reload");
        },
    });

    expect(".o_data_row").toHaveCount(4);
    expect(".o_optional_columns_dropdown_toggle").toHaveCount(1);

    await click(".o_optional_columns_dropdown_toggle");
    await animationFrame();
    const dropdown = getDropdownMenu(".o_optional_columns_dropdown");

    expect(queryAll(".dropdown-item", { root: dropdown })).toHaveCount(2);
    expect(queryAll(".dropdown-item-studio", { root: dropdown })).toHaveCount(1);

    await click(".dropdown-item-studio");
    await animationFrame();
    expect(".modal-studio").toHaveCount(1);

    await click(".modal .o_install_studio");
    await animationFrame();
    expect(browser.localStorage.getItem("openStudioOnReload")).toBe("main");
    expect.verifySteps(["studio_module_id", "studio_module_install", "window_reload"]);
});

test("add custom field button without other optional columns - studio not installed", async () => {
    expect.assertions(8);

    onRpc("search_read", ({ model }) => {
        if (model === "ir.module.module") {
            expect.step("studio_module_id");
            return [{ id: 42 }];
        }
    });
    onRpc("button_immediate_install", ({ model, args }) => {
        if (model === "ir.module.module") {
            expect(args[0]).toEqual([42], {
                message: "Should be the id of studio module returned by the search read",
            });
            expect.step("studio_module_install");
            return true;
        }
    });
    await mountView({
        type: "list",
        resModel: "foo",
        config: getDefaultConfig(),
        arch: /* xml */ `
            <list>
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
    });

    patchWithCleanup(browser.location, {
        reload: function () {
            expect.step("window_reload");
        },
    });

    expect(".o_data_row").toHaveCount(4);
    expect(".o_optional_columns_dropdown_toggle").toHaveCount(1);

    await click(".o_optional_columns_dropdown_toggle");
    await animationFrame();
    const dropdown = getDropdownMenu(".o_optional_columns_dropdown");

    expect(queryAll(".dropdown-item", { root: dropdown })).toHaveCount(1);
    expect(queryAll(".dropdown-item-studio", { root: dropdown })).toHaveCount(1);

    await click(".dropdown-item-studio");
    await animationFrame();
    expect(".modal-studio").toHaveCount(1);

    await click(".modal .o_install_studio");
    await animationFrame();
    expect(browser.localStorage.getItem("openStudioOnReload")).toBe("main");
    expect.verifySteps(["studio_module_id", "studio_module_install", "window_reload"]);
});

test("add custom field button not shown to non-system users (with opt. col.)", async () => {
    expect.assertions(3);

    patchWithCleanup(user, { isSystem: false });

    await mountView({
        type: "list",
        resModel: "foo",
        config: getDefaultConfig(),
        arch: /* xml */ `
            <list>
                <field name="foo"/>
                <field name="bar" optional="hide"/>
            </list>
        `,
    });

    expect(".o_optional_columns_dropdown_toggle").toHaveCount(1);

    await click(".o_optional_columns_dropdown_toggle");
    await animationFrame();
    const dropdown = getDropdownMenu(".o_optional_columns_dropdown");
    expect(queryAll(".dropdown-item", { root: dropdown })).toHaveCount(1);
    expect(queryAll(".dropdown-item-studio", { root: dropdown })).toHaveCount(0);
});

test("add custom field button not shown to non-system users (wo opt. col.)", async () => {
    patchWithCleanup(user, { isSystem: false });

    await mountView({
        type: "list",
        resModel: "foo",
        config: getDefaultConfig(),
        arch: /* xml */ `
            <list>
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
    });

    expect(".o_optional_columns_dropdown_toggle").toHaveCount(0);
});

test("add custom field button not shown with invalid action", async () => {
    expect.assertions(1);

    patchWithCleanup(user, { isSystem: false });

    await mountView({
        type: "list",
        resModel: "foo",
        config: { ...getDefaultConfig(), actionId: null },
        arch: /* xml */ `
            <list>
                <field name="foo"/>
                <field name="bar"/>
            </list>
        `,
    });

    expect(".o_optional_columns_dropdown_toggle").toHaveCount(0);
});

test("add custom field button not shown with bank statement line model", async () => {
    class AccountBankStatementLine extends models.Model {
        name = fields.Char();
        _views = {
            kanban: `
                <kanban>
                    <template>
                        <t t-name="card">
                            <field name="display_name"/>
                        </t>
                    </template>
                </kanban>
            `,
            list: `<list><field name="display_name" /> <field name="name" optional="1" /></list>`,
        };
    }
    defineModels([AccountBankStatementLine]);

    expect.assertions(3);

    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    await getService("action").doAction({
        xml_id: "test",
        id: 1312,
        name: "test",
        res_id: 1,
        res_model: "account.bank.statement.line",
        type: "ir.actions.act_window",
        views: [[false, "kanban"], [false, "list"]],
    });

    expect("button.o_switch_view.o_list[data-tooltip='List']").toHaveCount(1);
    await contains("button.o_switch_view.o_list[data-tooltip='List']").click();
    expect(".o_list_renderer .o_list_controller button.dropdown-toggle").toHaveCount(1);
    await contains(".o_list_renderer .o_list_controller button.dropdown-toggle").click();
    expect(".dropdown-item-studio").toHaveCount(0);
});

test("x2many should not be editable", async () => {
    class Bar extends models.Model {}
    defineModels([Bar]);
    Foo._fields.o2m = fields.One2many({ relation: "bar" });

    await mountView({
        type: "form",
        resModel: "foo",
        arch: /* xml */ `
            <form>
                <notebook>
                    <page>
                        <field name="o2m">
                            <list>
                                <field name="display_name"/>
                            </list>
                        </field>
                    </page>
                    <page><div class="test_empty_page" /></page>
                </notebook>
            </form>
        `,
    });
    expect(".o_optional_columns_dropdown_toggle").toHaveCount(0);
    await click(".nav-link:eq(1)");
    await animationFrame();
    await click(".nav-link:eq(0)");
    await animationFrame();
    expect(".o_field_widget").toHaveCount(1);
    expect(".o_optional_columns_dropdown_toggle").toHaveCount(0);
});

test("upsell studio feature is not polluted by another view", async () => {
    class Partner extends models.Model {
        name = fields.Char();

        _views = {
            list: `<list><field name="display_name" /> <field name="name" optional="1" /></list>`,
        };
    }

    defineModels([Partner]);

    await mountWithCleanup(WebClientEnterprise);
    await animationFrame();

    await getService("action").doAction({
        xml_id: "editable",
        id: 999,
        type: "ir.actions.act_window",
        views: [[false, "list"]],
        res_model: "partner",
    });

    await click(".o_optional_columns_dropdown_toggle");
    await animationFrame();
    expect(".dropdown-item").toHaveCount(2);
    expect(".dropdown-item-studio").toHaveCount(1);

    await getService("action").doAction({
        id: 99,
        xml_id: "in_dialog",
        type: "ir.actions.act_window",
        views: [[false, "list"]],
        res_model: "partner",
        target: "new",
    });

    await click(".modal .o_optional_columns_dropdown_toggle");
    await animationFrame();
    let dropdown = getDropdownMenu(".modal .o_optional_columns_dropdown");
    expect(queryAll(".dropdown-item", { root: dropdown })).toHaveCount(1);
    expect(queryAll(".dropdown-item-studio", { root: dropdown })).toHaveCount(0);
    await click(".modal-header .btn-close");
    await animationFrame();
    expect(".modal").toHaveCount(0);

    await click(".o_optional_columns_dropdown_toggle");
    await animationFrame();
    expect(".o-dropdown--menu").toHaveCount(0);
    await click(".o_optional_columns_dropdown_toggle");
    await animationFrame();

    dropdown = getDropdownMenu(".o_optional_columns_dropdown");
    expect(queryAll(".dropdown-item", { root: dropdown })).toHaveCount(2);
    expect(queryAll(".dropdown-item-studio", { root: dropdown })).toHaveCount(1);
});
