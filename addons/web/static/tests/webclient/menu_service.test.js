import { expect, test } from "@odoo/hoot";
import { redirect } from "@web/core/utils/urls";
import {
    defineActions,
    defineMenus,
    defineModels,
    fields,
    models,
    mountWebClient,
    onRpc,
    webModels,
} from "@web/../tests/web_test_helpers";
import { browser } from "@web/core/browser/browser";
import { Deferred } from "@odoo/hoot-mock";
import { animationFrame } from "@odoo/hoot-dom";

defineActions([
    {
        id: 666,
        xml_id: "action_1",
        name: "Partners Action 1",
        res_model: "partner",
        views: [[false, "kanban"]],
    },
]);

class Partner extends models.Model {
    name = fields.Char();
    foo = fields.Char();

    _records = [
        { id: 1, name: "First record", foo: "yop" },
        { id: 2, name: "Second record", foo: "blip" },
        { id: 3, name: "Third record", foo: "gnap" },
        { id: 4, name: "Fourth record", foo: "plop" },
        { id: 5, name: "Fifth record", foo: "zoup" },
    ];
    _views = {
        kanban: `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="foo"/>
                    </t>
                </templates>
            </kanban>
        `,
        list: `<list><field name="foo"/></list>`,
        form: `
            <form>
                <group>
                    <field name="display_name"/>
                    <field name="foo"/>
                </group>
            </form>
        `,
        search: `<search><field name="foo" string="Foo"/></search>`,
    };
}
const { ResCompany, ResPartner, ResUsers } = webModels;
defineModels([Partner, ResCompany, ResPartner, ResUsers]);
defineMenus([
    {
        id: 1,
        children: [
            { id: 2, name: "Test1", appID: 1, actionID: 666 },
            { id: 3, name: "Test2", appID: 1, actionID: 666 },
        ],
        name: "App1",
        appID: 1,
        actionID: 666,
    },
]);

test.tags("desktop");
test(`use stored menus, and don't update on load_menus return (if identical)`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", () => def);

    // Initial Stored values
    browser.localStorage.webclient_menus_version =
        "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { appID: 1, children: [2, 3], name: "App1", id: 1, actionID: 666 },
        2: { appID: 1, children: [], name: "Test1", id: 2, actionID: 666 },
        3: { appID: 1, children: [], name: "Test2", id: 3, actionID: 666 },
        root: { id: "root", name: "root", appID: "root", children: [1] },
    });

    const webClient = await mountWebClient();
    webClient.env.bus.addEventListener("MENUS:APP-CHANGED", () => expect.step("Don't Update"));
    expect(`.o_menu_brand`).toHaveText("App1");
    expect(browser.sessionStorage.getItem("menu_id")).toBe("1");
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    def.resolve();
    await animationFrame();
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect.verifySteps([]);
});

test.tags("desktop");
test(`use stored menus, and update on load_menus return`, async () => {
    const def = new Deferred();
    redirect("/odoo/action-666");
    onRpc("/web/webclient/load_menus", () => def);

    // Initial Stored values
    // There is no menu "Test2" in the initial values
    browser.localStorage.webclient_menus_version =
        "05500d71e084497829aa807e3caa2e7e9782ff702c15b2f57f87f2d64d049bd0";
    browser.localStorage.webclient_menus = JSON.stringify({
        1: { id: 1, children: [2], name: "App1", appID: 1, actionID: 666 },
        2: { id: 2, children: [], name: "Test1", appID: 1, actionID: 666 },
        root: { id: "root", children: [1], name: "root", appID: "root" },
    });

    const webClient = await mountWebClient();
    webClient.env.bus.addEventListener("MENUS:APP-CHANGED", () => expect.step("Update Menus"));
    expect(`.o_menu_brand`).toHaveText("App1");
    expect(browser.sessionStorage.getItem("menu_id")).toBe("1");
    expect(".o_menu_sections").toHaveText("Test1");
    expect.verifySteps([]);
    def.resolve();
    await animationFrame();
    expect(".o_menu_sections").toHaveText("Test1\nTest2");
    expect(JSON.parse(browser.localStorage.webclient_menus)).toEqual({
        1: {
            actionID: 666,
            appID: 1,
            children: [2, 3],
            id: 1,
            name: "App1",
        },
        2: {
            actionID: 666,
            appID: 1,
            children: [],
            id: 2,
            name: "Test1",
        },
        3: {
            actionID: 666,
            appID: 1,
            children: [],
            id: 3,
            name: "Test2",
        },
        root: {
            appID: "root",
            children: [1],
            id: "root",
            name: "root",
        },
    });
    expect.verifySteps(["Update Menus"]);
});
