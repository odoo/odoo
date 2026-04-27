import { describe, test } from "@odoo/hoot";
import { click, contains, start, startServer } from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { serverState } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("The partner's phone number is displayed in correspondence details.", async () => {
    const pyEnv = await startServer();
    const phoneNumber = "355 649 6295";
    pyEnv["res.partner"].create({ name: "Maxime Randonnées", phone: phoneNumber });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await click(".list-group-item-action", { text: "Maxime Randonnées" });
    await contains(`[href$="${phoneNumber}"] .fa-phone`);
});

test("The partner's mobile number is displayed in correspondence details.", async () => {
    const pyEnv = await startServer();
    const phoneNumber = "0456 703 6196";
    pyEnv["res.partner"].create({ name: "Maxime Randonnées", mobile: phoneNumber });
    await start();
    await click(".o_menu_systray button[title='Open Softphone']");
    await click(".nav-link", { text: "Contacts" });
    await click(".list-group-item-action", { text: "Maxime Randonnées" });
    await contains(`[href$="${phoneNumber}"] .fa-mobile`);
});

test("Calls are properly displayed even if their state is broken.", async () => {
    const pyEnv = await startServer();
    // If for some reason (e.g. a power outage in the middle of a call) the call
    // is never properly terminated, it may be stuck in the “calling” or
    // “ongoing” state. Let's mock this situation:
    pyEnv["voip.call"].create({
        phone_number: "+263-735-552-56",
        state: "calling",
        user_id: serverState.userId,
    });
    pyEnv["voip.call"].create({
        phone_number: "+32-495-558-286",
        state: "ongoing",
        user_id: serverState.userId,
    });
    await start();
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
