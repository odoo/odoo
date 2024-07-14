/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("correspondence_details");

QUnit.test("The partner's phone number is displayed in correspondence details.", async () => {
    const pyEnv = await startServer();
    const phoneNumber = "355 649 6295";
    pyEnv["res.partner"].create({ display_name: "Maxime Randonnées", phone: phoneNumber });
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await click(".list-group-item-action", { text: "Maxime Randonnées" });
    await contains(`[href$="${phoneNumber}"] .fa-phone`);
});

QUnit.test("The partner's mobile number is displayed in correspondence details.", async () => {
    const pyEnv = await startServer();
    const phoneNumber = "0456 703 6196";
    pyEnv["res.partner"].create({ display_name: "Maxime Randonnées", mobile: phoneNumber });
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await click(".list-group-item-action", { text: "Maxime Randonnées" });
    await contains(`[href$="${phoneNumber}"] .fa-mobile`);
});

QUnit.test("Calls are properly displayed even if their state is broken.", async () => {
    const pyEnv = await startServer();
    // If for some reason (e.g. a power outage in the middle of a call) the call
    // is never properly terminated, it may be stuck in the “calling” or
    // “ongoing” state. Let's mock this situation:
    pyEnv["voip.call"].create({ phone_number: "+263-735-552-56", state: "calling", user_id: pyEnv.currentUserId });
    pyEnv["voip.call"].create({ phone_number: "+32-495-558-286", state: "ongoing", user_id: pyEnv.currentUserId });
    start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Recent" });
    await click(".list-group-item-action", { text: "Call to +263-735-552-56" });
    await contains(".o-voip-CorrespondenceDetails");
    await contains(".o-voip-CorrespondenceDetails .bg-success.bg-opacity-25", { count: 0 });
    await contains("button[title='End Call']", { count: 0 });
    await click("button[title='Close details']");
    await click(".list-group-item-action", { text: "Call to +32-495-558-286" });
    await contains(".o-voip-CorrespondenceDetails");
    await contains(".o-voip-CorrespondenceDetails .bg-success.bg-opacity-25", { count: 0 });
    await contains("button[title='End Call']", { count: 0 });
});
