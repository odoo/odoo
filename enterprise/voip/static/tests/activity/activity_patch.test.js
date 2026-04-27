import { describe, expect, test } from "@odoo/hoot";
import {
    click,
    contains,
    openFormView,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";

describe.current.tags("desktop");
setupVoipTests();

test("Landline number is displayed in activity info.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        phone: "+1-202-555-0182",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity-voip-landline-number", { text: "+1-202-555-0182" });
});

test("Mobile number is displayed in activity info.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        mobile: "4567829775",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity-voip-mobile-number", { text: "4567829775" });
});

test("When both landline and mobile numbers are provided, a prefix is added to distinguish the two in activity info.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        phone: "+1-202-555-0182",
        mobile: "4567829775",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity-voip-mobile-number", { text: "Mobile: 4567829775" });
    await contains(".o-mail-Activity-voip-landline-number", { text: "Phone: +1-202-555-0182" });
});

test("Click on landline number from activity info triggers a call.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        phone: "+1-202-555-0182",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity-voip-landline-number > a");
    expect(pyEnv["voip.call"].search_count([["phone_number", "=", "+1-202-555-0182"]])).toBe(1);
});

test("Click on mobile number from activity info triggers a call.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        mobile: "4567829775",
        res_id: partnerId,
        res_model: "res.partner",
    });
    await start();
    await openFormView("res.partner", partnerId);
    await click(".o-mail-Activity-voip-mobile-number > a");
    expect(pyEnv["voip.call"].search_count([["phone_number", "=", "4567829775"]])).toBe(1);
});
