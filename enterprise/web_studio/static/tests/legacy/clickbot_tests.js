/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SUCCESS_SIGNAL } from "@web/webclient/clickbot/clickbot";
import { createEnterpriseWebClient } from "@web_enterprise/../tests/helpers";
import { registerStudioDependencies } from "./helpers";
import { makeDeferred, patchDate, patchWithCleanup } from "@web/../tests/helpers/utils";
import { browser } from "@web/core/browser/browser";

let serverData;
let clickEverywhereDef;

QUnit.module("Studio clickbot", (hooks) => {
    hooks.beforeEach(async function () {
        serverData = {
            models: {
                foo: {
                    fields: {
                        foo: { string: "Foo", type: "char" },
                        bar: { string: "Bar", type: "boolean" },
                        date: { string: "Some Date", type: "date" },
                    },
                    records: [
                        {
                            id: 1,
                            bar: true,
                            foo: "yop",
                            date: "2017-01-25",
                        },
                        {
                            id: 2,
                            bar: true,
                            foo: "blip",
                        },
                        {
                            id: 3,
                            bar: true,
                            foo: "gnap",
                        },
                        {
                            id: 4,
                            bar: false,
                            foo: "blip",
                        },
                    ],
                },
            },
            views: {
                "foo,false,search": `
                    <search>
                        <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                        <filter string="Date" name="date" date="date"/>
                    </search>`,
                "foo,false,list": `
                    <list>
                        <field name="foo" />
                    </list>`,
                "foo,false,kanban": `
                <kanban class="o_kanban_test">
                    <templates><t t-name="card">
                        <field name="foo"/>
                    </t></templates>
                </kanban>`,
            },
        };
        registry.category("command_categories").add("view_switcher", {});
        registerStudioDependencies();
    });
    QUnit.test("clickbot clickeverywhere test", async (assert) => {
        patchDate(2017, 9, 8, 15, 35, 11); // October 8 2017, 15:35:11
        serverData.actions = {
            1001: {
                id: 1001,
                name: "App1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [
                    [false, "list"],
                    [false, "kanban"],
                ],
                xml_id: "app1",
            },
            1002: {
                id: 1002,
                name: "App2 Menu 1",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[false, "kanban"]],
                xml_id: "app2_menu1",
            },
            1022: {
                id: 1022,
                name: "App2 Menu 2",
                res_model: "foo",
                type: "ir.actions.act_window",
                views: [[false, "list"]],
                xml_id: "app2_menu2",
            },
        };
        serverData.menus = {
            root: { id: "root", children: [1, 2], name: "root", appID: "root" },
            1: { id: 1, children: [], name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
            2: {
                id: 2,
                children: [3, 4],
                name: "App2",
                appID: 2,
                actionID: 1002,
                xmlid: "app2",
            },
            3: {
                id: 3,
                children: [],
                name: "menu 1",
                appID: 2,
                actionID: 1002,
                xmlid: "app2_menu1",
            },
            4: {
                id: 4,
                children: [],
                name: "menu 2",
                appID: 2,
                actionID: 1022,
                xmlid: "app2_menu1",
            },
        };
        patchWithCleanup(odoo, { info: { isEnterprise: 1 } });
        patchWithCleanup(browser, {
            console: {
                log: (msg) => {
                    assert.step(msg);
                    if (msg === SUCCESS_SIGNAL) {
                        clickEverywhereDef.resolve();
                    }
                },
                error: (msg) => {
                    assert.step(msg);
                    clickEverywhereDef.resolve();
                },
            },
        });
        await createEnterpriseWebClient({ serverData });
        clickEverywhereDef = makeDeferred();
        window.clickEverywhere();
        await clickEverywhereDef;
        assert.verifySteps([
            "Testing app menu: app1",
            "Testing menu App1 app1",
            'Clicking on: menu item "App1"',
            "Clicking on: entering studio",
            "Clicking on: leaving studio",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing view switch: kanban",
            "Clicking on: kanban view switcher",
            "Clicking on: entering studio",
            "Clicking on: leaving studio",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Clicking on: home menu toggle button",
            "Testing app menu: app2",
            "Testing menu App2 app2",
            'Clicking on: menu item "App2"',
            "Clicking on: entering studio",
            "Clicking on: leaving studio",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 1 app2_menu1",
            'Clicking on: menu item "menu 1"',
            "Clicking on: entering studio",
            "Clicking on: leaving studio",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Testing menu menu 2 app2_menu1",
            'Clicking on: menu item "menu 2"',
            "Clicking on: entering studio",
            "Clicking on: leaving studio",
            "Testing 2 filters",
            'Clicking on: filter "Not Bar"',
            'Clicking on: filter "Date"',
            'Clicking on: filter option "October"',
            "Successfully tested 2 apps",
            "Successfully tested 2 menus",
            "Successfully tested 0 modals",
            "Successfully tested 10 filters",
            "Successfully tested 5 views in Studio",
            SUCCESS_SIGNAL,
        ]);
    });
});
