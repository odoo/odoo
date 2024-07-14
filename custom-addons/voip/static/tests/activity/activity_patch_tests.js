/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";

QUnit.module("activity");

QUnit.test("Landline number is displayed in activity info.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        phone: "+1-202-555-0182",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity-voip-landline-number", { text: "+1-202-555-0182" });
});

QUnit.test("Mobile number is displayed in activity info.", async () => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        mobile: "4567829775",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await contains(".o-mail-Activity-voip-mobile-number", { text: "4567829775" });
});

QUnit.test(
    "When both landline and mobile numbers are provided, a prefix is added to distinguish the two in activity info.",
    async () => {
        const pyEnv = await startServer();
        const partnerId = pyEnv["res.partner"].create({});
        pyEnv["mail.activity"].create({
            phone: "+1-202-555-0182",
            mobile: "4567829775",
            res_id: partnerId,
            res_model: "res.partner",
        });
        const { openFormView } = await start();
        openFormView("res.partner", partnerId);
        await contains(".o-mail-Activity-voip-mobile-number", { text: "Mobile: 4567829775" });
        await contains(".o-mail-Activity-voip-landline-number", { text: "Phone: +1-202-555-0182" });
    }
);

QUnit.test("Click on landline number from activity info triggers a call.", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        phone: "+1-202-555-0182",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click(".o-mail-Activity-voip-landline-number > a");
    assert.strictEqual(
        pyEnv["voip.call"].searchCount([["phone_number", "=", "+1-202-555-0182"]]),
        1
    );
});

QUnit.test("Click on mobile number from activity info triggers a call.", async (assert) => {
    const pyEnv = await startServer();
    const partnerId = pyEnv["res.partner"].create({});
    pyEnv["mail.activity"].create({
        mobile: "4567829775",
        res_id: partnerId,
        res_model: "res.partner",
    });
    const { openFormView } = await start();
    openFormView("res.partner", partnerId);
    await click(".o-mail-Activity-voip-mobile-number > a");
    assert.strictEqual(pyEnv["voip.call"].searchCount([["phone_number", "=", "4567829775"]]), 1);
});
