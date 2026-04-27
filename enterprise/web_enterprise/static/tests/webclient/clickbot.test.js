import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { Deferred, mockDate } from "@odoo/hoot-mock";
import {
    defineActions,
    defineMenus,
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { browser } from "@web/core/browser/browser";
import { WebClient } from "@web/webclient/webclient";
import { SUCCESS_SIGNAL } from "@web/webclient/clickbot/clickbot";

class Foo extends models.Model {
    foo = fields.Char();
    bar = fields.Boolean();
    date = fields.Date();

    _records = [
        { id: 1, bar: true, foo: "yop", date: "2017-01-25" },
        { id: 2, bar: true, foo: "blip" },
        { id: 3, bar: true, foo: "gnap" },
        { id: 4, bar: false, foo: "blip" },
    ];

    _views = {
        search: /* xml */ `
            <search>
                <filter string="Not Bar" name="not bar" domain="[['bar','=',False]]"/>
                <filter string="Date" name="date" date="date"/>
            </search>
        `,
        list: /* xml */ `
            <list>
                <field name="foo" />
            </list>
        `,
        kanban: /* xml */ `
            <kanban class="o_kanban_test">
                <templates><t t-name="card">
                    <field name="foo"/>
                </t></templates>
            </kanban>
        `,
    };
}

describe.current.tags("desktop");

defineModels([Foo]);

beforeEach(() => {
    defineActions([
        {
            id: 1001,
            name: "App1",
            res_model: "foo",
            views: [
                [false, "list"],
                [false, "kanban"],
            ],
            xml_id: "app1",
        },
        {
            id: 1002,
            name: "App2 Menu 1",
            res_model: "foo",
            views: [[false, "kanban"]],
            xml_id: "app2_menu1",
        },
        {
            id: 1022,
            name: "App2 Menu 2",
            res_model: "foo",
            views: [[false, "list"]],
            xml_id: "app2_menu2",
        },
    ]);
    defineMenus([
        { id: 1, name: "App1", appID: 1, actionID: 1001, xmlid: "app1" },
        {
            id: 2,
            children: [
                {
                    id: 3,
                    name: "menu 1",
                    appID: 2,
                    actionID: 1002,
                    xmlid: "app2_menu1",
                },
                {
                    id: 4,
                    name: "menu 2",
                    appID: 2,
                    actionID: 1022,
                    xmlid: "app2_menu2",
                },
            ],
            name: "App2",
            appID: 2,
            actionID: 1002,
            xmlid: "app2",
        },
    ]);
});

test("clickbot clickeverywhere test", async () => {
    onRpc("has_group", () => true);
    mockDate("2017-10-08T15:35:11.000");
    const clickEverywhereDef = new Deferred();
    patchWithCleanup(browser, {
        console: {
            log: (msg) => {
                expect.step(msg);
                if (msg === SUCCESS_SIGNAL) {
                    clickEverywhereDef.resolve();
                }
            },
            error: (msg) => {
                expect.step(msg);
                clickEverywhereDef.resolve();
            },
        },
    });
    const webClient = await mountWithCleanup(WebClient);
    patchWithCleanup(odoo, {
        __WOWL_DEBUG__: { root: webClient },
    });
    window.clickEverywhere();
    await clickEverywhereDef;
    expect.verifySteps([
        "Clicking on: apps menu toggle button",
        "Testing app menu: app1",
        "Testing menu App1 app1",
        'Clicking on: menu item "App1"',
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Testing view switch: kanban",
        "Clicking on: kanban view switcher",
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Clicking on: apps menu toggle button",
        "Testing app menu: app2",
        "Testing menu App2 app2",
        'Clicking on: menu item "App2"',
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Testing menu menu 1 app2_menu1",
        'Clicking on: menu item "menu 1"',
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Testing menu menu 2 app2_menu2",
        'Clicking on: menu item "menu 2"',
        "Testing 2 filters",
        'Clicking on: filter "Not Bar"',
        'Clicking on: filter "Date"',
        'Clicking on: filter option "October"',
        "Successfully tested 2 apps",
        "Successfully tested 2 menus",
        "Successfully tested 0 modals",
        "Successfully tested 10 filters",
        SUCCESS_SIGNAL,
    ]);
});
