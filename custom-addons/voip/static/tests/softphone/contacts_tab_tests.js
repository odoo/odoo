/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains, insertText } from "@web/../tests/utils";

QUnit.module("contacts_tab");

QUnit.test("Partners with a phone number are displayed in Contacts tab", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create([
        { display_name: "Michel Landline", phone: "+1-307-555-0120" },
        { display_name: "Maxim Mobile", mobile: "+257 114 7579" },
        { display_name: "Patrice Nomo" },
    ]);
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await contains(".o-voip-ContactsTab .list-group-item-action", { count: 2 });
    await contains(".o-voip-ContactsTab b", { text: "Michel Landline" });
    await contains(".o-voip-ContactsTab b", { text: "Maxim Mobile" });
    await contains(".o-voip-ContactsTab b", { text: "Patrice Nomo", count: 0 });
});

QUnit.test("Typing in the search bar fetches and displays the matching contacts", async () => {
    const pyEnv = await startServer();
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    pyEnv["res.partner"].create([
        { display_name: "Morshu RTX", phone: "+61-855-527-77" },
        { display_name: "Gargamel", mobile: "+61-855-583-671" },
    ]);
    await insertText("input[placeholder=Search]", "Morshu");
    await contains(".o-voip-ContactsTab b", { text: "Morshu RTX" });
    await contains(".o-voip-ContactsTab b", { text: "Gargamel", count: 0 });
});
