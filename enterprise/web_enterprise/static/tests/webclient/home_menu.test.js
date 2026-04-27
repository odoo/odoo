import { describe, expect, test } from "@odoo/hoot";
import { click, drag, keyDown, pointerDown, queryFirst } from "@odoo/hoot-dom";
import { advanceTime, animationFrame, mockDate, mockTouch } from "@odoo/hoot-mock";
import {
    getService,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

import { reactive } from "@odoo/owl";
import { session } from "@web/session";
import { HomeMenu } from "@web_enterprise/webclient/home_menu/home_menu";
import { reorderApps } from "@web/webclient/menus/menu_helpers";

async function walkOn(path) {
    for (const step of path) {
        await keyDown(`${step.shiftKey ? "shift+" : ""}${step.key}`);
        await animationFrame();
        expect(`.o_menuitem:eq(${step.index})`).toHaveClass("o_focused", {
            message: `step ${step.number}`,
        });
    }
}

const getDefaultHomeMenuProps = () => {
    const apps = [
        {
            actionID: 121,
            href: "/odoo/action-121",
            appID: 1,
            id: 1,
            label: "Discuss",
            parents: "",
            webIcon: false,
            xmlid: "app.1",
        },
        {
            actionID: 122,
            href: "/odoo/action-122",
            appID: 2,
            id: 2,
            label: "Calendar",
            parents: "",
            webIcon: false,
            xmlid: "app.2",
        },
        {
            actionID: 123,
            href: "/odoo/contacts",
            appID: 3,
            id: 3,
            label: "Contacts",
            parents: "",
            webIcon: false,
            xmlid: "app.3",
        },
    ];
    return { apps, reorderApps: (order) => reorderApps(apps, order) };
};

describe.current.tags("desktop");

test("ESC Support", async () => {
    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    patchWithCleanup(getService("home_menu"), {
        async toggle(show) {
            expect.step(`toggle ${show}`);
        },
    });
    await keyDown("escape");
    expect.verifySteps(["toggle false"]);
});

test("Click on an app", async () => {
    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    patchWithCleanup(getService("menu"), {
        async selectMenu(menu) {
            expect.step(`selectMenu ${menu.id}`);
        },
    });
    await click(".o_menuitem:eq(0)");
    await animationFrame();
    expect.verifySteps(["selectMenu 1"]);
});

test("Display Expiration Panel (no module installed)", async () => {
    mockDate("2019-10-09T00:00:00");

    patchWithCleanup(session, {
        expiration_date: "2019-11-01 12:00:00",
        expiration_reason: "",
        isMailInstalled: false,
        warning: "admin",
    });

    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });

    expect(".database_expiration_panel").toHaveCount(1);
    expect(".database_expiration_panel .oe_instance_register").toHaveText(
        "You will be able to register your database once you have installed your first app.",
        { message: "There should be an expiration panel displayed" }
    );

    // Close the expiration panel
    await click(".database_expiration_panel .oe_instance_hide_panel");
    await animationFrame();
    expect(".database_expiration_panel").toHaveCount(0);
});

test("Navigation (only apps, only one line)", async () => {
    expect.assertions(8);

    const homeMenuProps = {
        apps: new Array(3).fill().map((x, i) => ({
            actionID: 120 + i,
            href: "/odoo/act" + (120 + i),
            appID: i + 1,
            id: i + 1,
            label: `0${i}`,
            parents: "",
            webIcon: false,
            xmlid: `app.${i}`,
        })),
        reorderApps: (order) => reorderApps(homeMenuProps.apps, order),
    };
    await mountWithCleanup(HomeMenu, {
        props: homeMenuProps,
    });

    const path = [
        { number: 0, key: "ArrowDown", index: 0 },
        { number: 1, key: "ArrowRight", index: 1 },
        { number: 2, key: "Tab", index: 2 },
        { number: 3, key: "ArrowRight", index: 0 },
        { number: 4, key: "Tab", shiftKey: true, index: 2 },
        { number: 5, key: "ArrowLeft", index: 1 },
        { number: 6, key: "ArrowDown", index: 1 },
        { number: 7, key: "ArrowUp", index: 1 },
    ];

    await walkOn(path);
});

test("Navigation (only apps, two lines, one incomplete)", async () => {
    expect.assertions(19);

    const homeMenuProps = {
        apps: new Array(8).fill().map((x, i) => ({
            actionID: 121,
            href: "/odoo/action-121",
            appID: i + 1,
            id: i + 1,
            label: `0${i}`,
            parents: "",
            webIcon: false,
            xmlid: `app.${i}`,
        })),
        reorderApps: (order) => reorderApps(homeMenuProps.apps, order),
    };
    await mountWithCleanup(HomeMenu, {
        props: homeMenuProps,
    });

    const path = [
        { number: 1, key: "ArrowRight", index: 0 },
        { number: 2, key: "ArrowUp", index: 6 },
        { number: 3, key: "ArrowUp", index: 0 },
        { number: 4, key: "ArrowDown", index: 6 },
        { number: 5, key: "ArrowDown", index: 0 },
        { number: 6, key: "ArrowRight", index: 1 },
        { number: 7, key: "ArrowRight", index: 2 },
        { number: 8, key: "ArrowUp", index: 7 },
        { number: 9, key: "ArrowUp", index: 1 },
        { number: 10, key: "ArrowRight", index: 2 },
        { number: 11, key: "ArrowDown", index: 7 },
        { number: 12, key: "ArrowDown", index: 1 },
        { number: 13, key: "ArrowUp", index: 7 },
        { number: 14, key: "ArrowRight", index: 6 },
        { number: 15, key: "ArrowLeft", index: 7 },
        { number: 16, key: "ArrowUp", index: 1 },
        { number: 17, key: "ArrowLeft", index: 0 },
        { number: 18, key: "ArrowLeft", index: 5 },
        { number: 19, key: "ArrowRight", index: 0 },
    ];

    await walkOn(path);
});

test("Navigation and open an app in the home menu", async () => {
    expect.assertions(6);

    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    patchWithCleanup(getService("menu"), {
        async selectMenu(menu) {
            expect.step(`selectMenu ${menu.id}`);
        },
    });
    // No app selected so nothing to open
    await keyDown("enter");
    expect.verifySteps([]);

    const path = [
        { number: 0, key: "ArrowDown", index: 0 },
        { number: 1, key: "ArrowRight", index: 1 },
        { number: 2, key: "Tab", index: 2 },
        { number: 3, key: "shift+Tab", index: 1 },
    ];

    await walkOn(path);

    // open first app (Calendar)
    await keyDown("enter");

    expect.verifySteps(["selectMenu 2"]);
});

test("Reorder apps in home menu using drag and drop", async () => {
    const homeMenuProps = {
        apps: reactive(
            new Array(8).fill().map((x, i) => ({
                actionID: 121,
                href: "/odoo/action-121",
                appID: i + 1,
                id: i + 1,
                label: `0${i}`,
                parents: "",
                webIcon: false,
                xmlid: `app.${i}`,
            }))
        ),
        reorderApps: (order) => reorderApps(homeMenuProps.apps, order),
    };
    onRpc("set_res_users_settings", () => {
        expect.step(`set_res_users_settings`);
        return {
            id: 1,
            homemenu_config: '["app.1","app.2","app.3","app.0","app.4","app.5","app.6","app.7"]',
        };
    });
    await mountWithCleanup(HomeMenu, {
        props: homeMenuProps,
    });

    const { moveTo, drop } = await drag(".o_draggable:first-child");
    await advanceTime(250);
    expect(".o_draggable:first-child a").not.toHaveClass("o_dragged_app");
    await advanceTime(250);
    expect(".o_draggable:first-child a").toHaveClass("o_dragged_app");
    await moveTo(".o_draggable:first-child", {
        position: {
            x: 70,
            y: 35,
        },
        relative: true,
    });
    await drop(".o_draggable:not(.o_dragged):eq(3)");
    await animationFrame();
    expect.verifySteps(["set_res_users_settings"]);
    expect(".o_app:eq(0)").toHaveAttribute("data-menu-xmlid", "app.1", {
        message: "first displayed app has app.1 xmlid",
    });
    expect(".o_app:eq(3)").toHaveAttribute("data-menu-xmlid", "app.0", {
        message: "app 0 is now at 4th position",
    });
});

test("The HomeMenu input takes the focus when you press a key only if no other element is the activeElement", async () => {
    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    expect(".o_search_hidden").toBeFocused();

    const activeElement = document.createElement("div");
    getService("ui").activateElement(activeElement);
    // remove the focus from the input
    const otherInput = document.createElement("input");
    queryFirst(".o_home_menu").appendChild(otherInput);
    await pointerDown(otherInput);
    await pointerDown(document.body);
    expect(document.body).toBeFocused();
    expect(".o_command_palette_search input").not.toHaveCount();

    await keyDown("a");
    await animationFrame();
    expect(document.body).toBeFocused();
    expect(".o_command_palette_search input").not.toHaveCount();

    getService("ui").deactivateElement(activeElement);
    await keyDown("a");
    await animationFrame();
    expect(".o_command_palette_search input").toBeFocused();
});

test("The HomeMenu input does not take the focus if it is already on another input", async () => {
    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    expect(".o_search_hidden").toBeFocused();

    const otherInput = document.createElement("input");
    queryFirst(".o_home_menu").appendChild(otherInput);
    await pointerDown(otherInput);
    await keyDown("a");
    await animationFrame();
    expect(otherInput).toBeFocused();
    expect(".o_command_palette_search input").not.toHaveCount();

    otherInput.remove();
    await keyDown("a");
    await animationFrame();
    expect(".o_command_palette_search input").toBeFocused();
});

test("The HomeMenu input does not take the focus if it is already on a textarea", async () => {
    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    expect(".o_search_hidden").toBeFocused();

    const textarea = document.createElement("textarea");
    queryFirst(".o_home_menu").appendChild(textarea);
    await pointerDown(textarea);
    await keyDown("a");
    await animationFrame();
    expect(textarea).toBeFocused();
    expect(".o_command_palette_search input").not.toHaveCount();

    textarea.remove();
    await keyDown("a");
    await animationFrame();
    expect(".o_command_palette_search input").toBeFocused();
});

test("home search input shouldn't be focused on touch devices", async () => {
    mockTouch(true);
    await mountWithCleanup(HomeMenu, {
        props: getDefaultHomeMenuProps(),
    });
    expect(".o_search_hidden").not.toBeFocused({
        message: "home menu search input shouldn't have the focus",
    });
});
