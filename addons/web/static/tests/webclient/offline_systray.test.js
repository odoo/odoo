import { WebClient } from "@web/webclient/webclient";

import { animationFrame, expect, queryAllTexts, runAllTimers, test } from "@odoo/hoot";
import {
    contains,
    getService,
    mountWithCleanup,
    mockOffline,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";

test.tags("desktop");
test("offline systray item: basic rendering (desktop)", async () => {
    const setOffline = mockOffline();
    await mountWithCleanup(WebClient);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
    await setOffline(true);

    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(1);
    expect(`.o_menu_systray .o_nav_entry:first`).toHaveText("Working offline");

    await setOffline(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("mobile");
test("offline systray item: basic rendering (mobile)", async () => {
    const setOffline = mockOffline();
    await mountWithCleanup(WebClient);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
    await setOffline(true);

    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(1);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken:first`).toHaveAttribute(
        "data-tooltip",
        "Working offline"
    );

    await setOffline(false);
    expect(`.o_menu_systray .o_nav_entry.fa-chain-broken`).toHaveCount(0);
});

test.tags("desktop");
test("offline systray item: click to check connection (desktop)", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        return true;
    });
    await mountWithCleanup(WebClient);
    await setOffline(true);

    await contains(`.o_menu_systray .o_nav_entry .fa-chain-broken`).click();
    expect.verifySteps(["version_info"]);
    expect(getService("offline").offline).toBe(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("mobile");
test("offline systray item: click to check connection (mobile)", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", async () => {
        expect.step("version_info");
        return true;
    });
    await mountWithCleanup(WebClient);
    await setOffline(true);

    await contains(`.o_menu_systray .o_nav_entry .fa-chain-broken`).click();
    expect.verifySteps(["version_info"]);
    expect(getService("offline").offline).toBe(false);
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(0);
});

test.tags("desktop");
test("scheduledORM", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", () => new Response("", { status: 502 }), { pure: true });
    await mountWithCleanup(WebClient);
    patchWithCleanup(getService("action"), {
        async doAction(action, options) {
            expect.step({ action, options });
        },
    });
    await runAllTimers(); // execute time, wait for the start syncORM
    await getService("offline").setAvailableOffline(22, "form", { resId: false });
    await setOffline(true);

    getService("offline").scheduleORM(
        "partner",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 22,
                actionName: "Contacts",
                viewType: "form",
                changes: { name: "plop", phone: "2233" },
                displayName: "Nice plop",
                timeStamp: 1,
            },
        }
    );
    getService("offline").scheduleORM(
        "partner",
        "web_save",
        [[22]],
        {},
        {
            extras: {
                actionId: 22,
                actionName: "Contacts",
                viewType: "form",
                changes: { phone: "667788" },
                originalValues: { phone: "2244" },
                displayName: "Plop22",
                timeStamp: 20,
            },
        }
    );
    getService("offline").scheduleORM(
        "lead",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 33,
                actionName: "CRM",
                viewType: "kanban_quick_create",
                changes: { name: "Harold Bohy", email: "hab@odoo.com" },
                displayName: "Harold Bohy",
                timeStamp: 30,
            },
        }
    );

    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(1);
    expect(queryAllTexts`.o_menu_systray .o_nav_entry`).toEqual(["Working offline", ""]);
    await contains(`.o_menu_systray .o_nav_entry .fa-chain-broken`).click();
    expect(".o-dropdown--menu:visible").toHaveCount(1, { message: "dropdown should be visible" });
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(3);
    expect(queryAllTexts`.o-dropdown--menu .o_offline_systray_content div`).toEqual(
        [
            "CONTACTS",
            "Nice plop",
            "Created",
            "",
            "Plop22",
            "Edited",
            "",
            "CRM",
            "Harold Bohy",
            "Created",
            "",
        ],
        { message: "The scheduled orm are grouped by action Name!" }
    );
    expect(`.o-dropdown--menu .o-dropdown-item:not(.o_cursor_auto)`).toHaveCount(1, {
        message: "We can click on the one with viewType 'form' and previously visited",
    });
    // The one that is not viewType form, can't be clicked on, and have text muted !
    // The one that is not previously visited, can't be clickend on, and have text muted !
    expect(`.o-dropdown--menu .o-dropdown-item.o_cursor_auto`).toHaveCount(2);
    expect(`.o-dropdown--menu .o-dropdown-item div.text-muted`).toHaveCount(2);

    // remove one.
    await contains(`.o-dropdown--menu .o-dropdown-item:nth-child(3) button.btn`).click();
    await contains(`.modal-dialog .modal-footer button.btn-primary`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.o-dropdown--menu .o_offline_systray_content div`).toEqual([
        "CONTACTS",
        "Nice plop",
        "Created",
        "",
        "CRM",
        "Harold Bohy",
        "Created",
        "",
    ]);

    // click on one
    await contains(`.o-dropdown--menu .o-dropdown-item`).click();
    expect.verifySteps([
        {
            action: 22,
            options: {
                clearBreadcrumbs: true,
                props: {
                    offlineId: "881ba65a",
                    resId: undefined,
                },
                viewType: "form",
            },
        },
    ]);
});

test.tags("desktop");
test("scheduledORM: inError", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", () => new Response("", { status: 502 }), { pure: true });
    await mountWithCleanup(WebClient);
    await runAllTimers(); // execute time, wait for the start syncORM
    await setOffline(true);

    getService("offline").scheduleORM(
        "partner",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 22,
                actionName: "Contacts",
                viewType: "form",
                changes: { name: "plop", phone: "2233" },
                displayName: "Nice plop",
                timeStamp: 1,
            },
        }
    );

    getService("offline").scheduleORM(
        "lead",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 33,
                actionName: "CRM",
                viewType: "kanban_quick_create",
                changes: { name: "Cedric Lards Ennais", email: "cla@odoo.com" },
                displayName: "Cedric Lards Ennais",
                timeStamp: 40,
                error: true,
            },
        }
    );

    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry .fa-exclamation-circle`).toHaveCount(1);
    expect(queryAllTexts`.o_menu_systray .o_nav_entry`).toEqual(["Working offline", ""]);
    await contains(`.o_menu_systray .o_nav_entry .fa-exclamation-circle`).click();
    expect(".o-dropdown--menu:visible").toHaveCount(1, { message: "dropdown should be visible" });
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.o-dropdown--menu .o_offline_systray_content div`).toEqual([
        "CONTACTS",
        "Nice plop",
        "Created",
        "",
        "CRM",
        "Cedric Lards Ennais",
        "Created",
        "",
    ]);
    expect(`.o-dropdown--menu .o-dropdown-item .fa-exclamation-circle`).toHaveCount(1);
    expect(`.o-dropdown--menu .o-dropdown-item div.text-danger`).toHaveCount(1);
    expect(queryAllTexts`.o-dropdown--menu .o-dropdown-item div.text-danger`).toEqual([
        "Cedric Lards Ennais",
    ]);
});

test.tags("mobile");
test("scheduledORM: mobile", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", () => new Response("", { status: 502 }), { pure: true });
    await mountWithCleanup(WebClient);
    patchWithCleanup(getService("action"), {
        async doAction(action, options) {
            expect.step({ action, options });
        },
    });
    await runAllTimers(); // execute time, wait for the start syncORM
    await getService("offline").setAvailableOffline(22, "form", { resId: false });
    await setOffline(true);

    getService("offline").scheduleORM(
        "partner",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 22,
                actionName: "Contacts",
                viewType: "form",
                changes: { name: "plop", phone: "2233" },
                displayName: "Nice plop",
                timeStamp: 1,
            },
        }
    );
    getService("offline").scheduleORM(
        "partner",
        "web_save",
        [[22]],
        {},
        {
            extras: {
                actionId: 22,
                actionName: "Contacts",
                viewType: "form",
                changes: { phone: "667788" },
                originalValues: { phone: "2244" },
                displayName: "Plop22",
                timeStamp: 20,
            },
        }
    );
    getService("offline").scheduleORM(
        "lead",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 33,
                actionName: "CRM",
                viewType: "kanban_quick_create",
                changes: { name: "Harold Bohy", email: "hab@odoo.com" },
                displayName: "Harold Bohy",
                timeStamp: 30,
            },
        }
    );

    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry .fa-chain-broken`).toHaveCount(1);
    expect(queryAllTexts`.o_menu_systray .o_nav_entry`).toEqual(["", ""], {
        message: "no text on mobile",
    });
    await contains(`.o_menu_systray .o_nav_entry .fa-chain-broken`).click();
    await animationFrame();
    expect(".o-dropdown--menu:visible").toHaveCount(1, { message: "dropdown should be visible" });
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(3);
    expect(queryAllTexts`.o-dropdown--menu .o_offline_systray_content div`).toEqual(
        [
            "CONTACTS",
            "Nice plop",
            "Created",
            "",
            "Plop22",
            "Edited",
            "",
            "CRM",
            "Harold Bohy",
            "Created",
            "",
        ],
        { message: "The scheduled orm are grouped by action Name!" }
    );
    expect(`.o-dropdown--menu .o-dropdown-item:not(.o_cursor_auto)`).toHaveCount(1, {
        message: "We can click on the one with viewType 'form' and previously visited",
    });
    // The one that is not viewType form, can't clicked on, and have text muted !
    expect(`.o-dropdown--menu .o-dropdown-item.o_cursor_auto`).toHaveCount(2);
    expect(`.o-dropdown--menu .o-dropdown-item div.text-muted`).toHaveCount(2);

    // remove one.
    await contains(`.o-dropdown--menu .o-dropdown-item:nth-child(3) button.btn`).click();
    await contains(`.modal-dialog .modal-footer button.btn-primary`).click();
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.o-dropdown--menu .o_offline_systray_content div`).toEqual([
        "CONTACTS",
        "Nice plop",
        "Created",
        "",
        "CRM",
        "Harold Bohy",
        "Created",
        "",
    ]);

    // click on one
    await contains(`.o-dropdown--menu .o-dropdown-item`).click();
    expect.verifySteps([
        {
            action: 22,
            options: {
                clearBreadcrumbs: true,
                props: {
                    offlineId: "881ba65a",
                    resId: undefined,
                },
                viewType: "form",
            },
        },
    ]);
});

test.tags("mobile");
test("scheduledORM: inError mobile", async () => {
    const setOffline = mockOffline();
    onRpc("/web/webclient/version_info", () => new Response("", { status: 502 }), { pure: true });
    await mountWithCleanup(WebClient);
    await runAllTimers(); // execute time, wait for the start syncORM
    await setOffline(true);

    getService("offline").scheduleORM(
        "partner",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 22,
                actionName: "Contacts",
                viewType: "form",
                changes: { name: "plop", phone: "2233" },
                displayName: "Nice plop",
                timeStamp: 1,
            },
        }
    );

    getService("offline").scheduleORM(
        "lead",
        "web_save",
        [[]],
        {},
        {
            extras: {
                actionId: 33,
                actionName: "CRM",
                viewType: "kanban_quick_create",
                changes: { name: "Cedric Lards Ennais", email: "cla@odoo.com" },
                displayName: "Cedric Lards Ennais",
                timeStamp: 40,
                error: true,
            },
        }
    );

    await animationFrame();
    expect(`.o_menu_systray .o_nav_entry .fa-exclamation-circle`).toHaveCount(1);
    expect(queryAllTexts`.o_menu_systray .o_nav_entry`).toEqual(["", ""], {
        message: "no text in mobile",
    });
    await contains(`.o_menu_systray .o_nav_entry .fa-exclamation-circle`).click();
    await animationFrame();
    expect(".o-dropdown--menu:visible").toHaveCount(1, { message: "dropdown should be visible" });
    expect(`.o-dropdown--menu .o-dropdown-item`).toHaveCount(2);
    expect(queryAllTexts`.o-dropdown--menu .o_offline_systray_content div`).toEqual([
        "CONTACTS",
        "Nice plop",
        "Created",
        "",
        "CRM",
        "Cedric Lards Ennais",
        "Created",
        "",
    ]);
    expect(`.o-dropdown--menu .o-dropdown-item .fa-exclamation-circle`).toHaveCount(1);
    expect(`.o-dropdown--menu .o-dropdown-item div.text-danger`).toHaveCount(1);
    expect(queryAllTexts`.o-dropdown--menu .o-dropdown-item div.text-danger`).toEqual([
        "Cedric Lards Ennais",
    ]);
});
