/** @odoo-module */

import { session } from "@web/session";

import { makeView } from "@web/../tests/views/helpers";
import { getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";

import { getServerData, updateArch, setupTestEnv } from "./hr_timesheet_common_tests";


QUnit.module("hr_timesheet", (hooks) => {
    let target;
    let serverData;
    hooks.beforeEach(async function (assert) {
        setupTestEnv();
        serverData = getServerData();
        updateArch(serverData, { unit_amount: "timesheet_uom" });
        target = getFixture();
    });

    QUnit.module("timesheet_uom");

    QUnit.test("FloatTimeField is used when current company uom uses float_time widget", async function (assert) {
        await makeView({
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
        });
        const unitAmountInput = target.querySelector('div[name="unit_amount"] input');
        assert.equal(unitAmountInput.value, "01:00", "unit_amount is displayed as time");
    });

    QUnit.test("FloatTimeField is not dependent of timesheet_uom_factor of the current company when current company uom uses float_time widget", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_factor: 2 });
        await makeView({
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
        });
        const unitAmountInput = target.querySelector('div[name="unit_amount"] input');
        assert.equal(unitAmountInput.value, "01:00", "timesheet_uom_factor is not taken into account");
    });

    QUnit.test("FloatToggleField is used when current company uom uses float_toggle widget", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 2 });
        await makeView({
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
        });
        assert.containsOnce(target, 'div[name="unit_amount"] .o_field_float_toggle', "unit_amount is displayed as float toggle");
    });

    QUnit.test("FloatToggleField is dependent of timesheet_uom_factor of the current company when current company uom uses float_toggle widget", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 2, timesheet_uom_factor: 2 });
        await makeView({
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
        });
        assert.containsOnce(target, 'div[name="unit_amount"] .o_field_float_toggle:contains("2.00")', "timesheet_uom_factor is taken into account");
    });

    QUnit.test("FloatFactorField is used when the current_company uom is not part of the session uom", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 'dummy' });
        await makeView({
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
        });
        const unitAmountInput = target.querySelector('div[name="unit_amount"] input');
        assert.containsOnce(target, 'div[name="unit_amount"] input[inputmode="decimal"]', "unit_amount is displayed as float");
        assert.equal(unitAmountInput.value, "1.00", "unit_amount is not displayed as float and not as time");
        assert.containsNone(target, 'div[name="unit_amount"].o_field_float_toggle', "unit_amount is not displayed as float toggle");
    });

    QUnit.test("FloatFactorField is dependent of timesheet_uom_factor of the current company when current company uom uses float_toggle widget", async function (assert) {
        patchWithCleanup(session.user_companies.allowed_companies[1], { timesheet_uom_id: 'dummy', timesheet_uom_factor: 2 });
        await makeView({
            serverData,
            type: "form",
            resModel: "account.analytic.line",
            resId: 1,
        });
        const unitAmountInput = target.querySelector('div[name="unit_amount"] input');
        assert.equal(unitAmountInput.value, "2.00", "timesheet_uom_factor is taken into account");
    });

});
