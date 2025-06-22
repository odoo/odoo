/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";

import { start } from "@mail/../tests/helpers/test_utils";

import {
    editSelect,
    selectDropdownItem,
    patchTimeZone,
    patchWithCleanup,
    getFixture,
} from "@web/../tests/helpers/utils";
import testUtils from "@web/../tests/legacy/helpers/test_utils";
import { click, contains, insertText } from "@web/../tests/utils";
import { currencies } from "@web/core/currency";

let target;

QUnit.module("tracking value", {
    beforeEach() {
        target = getFixture();
        const views = {
            "mail.test.track.all,false,form": `<form>
                    <sheet>
                        <field name="boolean_field"/>
                        <field name="char_field"/>
                        <field name="date_field"/>
                        <field name="datetime_field"/>
                        <field name="float_field"/>
                        <field name="float_field_with_digits"/>
                        <field name="integer_field"/>
                        <field name="monetary_field"/>
                        <field name="many2one_field_id"/>
                        <field name="selection_field"/>
                        <field name="text_field"/>
                    </sheet>
                    <div class="oe_chatter">
                        <field name="message_ids"/>
                    </div>
                </form>`,
        };
        this.start = async ({ res_id }) => {
            const { openFormView, ...remainder } = await start({
                serverData: { views },
            });
            await openFormView("mail.test.track.all", res_id, {
                props: { mode: "edit" },
            });
            return remainder;
        };

        patchTimeZone(0);
    },
});

QUnit.test("basic rendering of tracking value (float type)", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({ float_field: 12.3 });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=float_field] input", "45.67", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking");
    await contains(".o-mail-Message-trackingField");
    await contains(".o-mail-Message-trackingField", { text: "(Float)" });
    await contains(".o-mail-Message-trackingOld");
    await contains(".o-mail-Message-trackingOld", { text: "12.30" });
    await contains(".o-mail-Message-trackingSeparator");
    await contains(".o-mail-Message-trackingNew");
    await contains(".o-mail-Message-trackingNew", { text: "45.67" });
});

QUnit.test("rendering of tracked field of type float: from non-0 to 0", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        float_field: 1,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=float_field] input", "0", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "1.000.00(Float)" });
});

QUnit.test("rendering of tracked field of type float: from 0 to non-0", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        float_field: 0,
        float_field_with_digits: 0,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=float_field] input", "1.01", { replace: true });
    await insertText("div[name=float_field_with_digits] input", "1.0001", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { count: 2 });
    const [defaultPrecisionLine, increasedPrecisionLine] =
        target.getElementsByClassName("o-mail-Message-tracking");
    const expectedText = [
        [defaultPrecisionLine, ["0.00", "1.01", "(Float)"]],
        [increasedPrecisionLine, ["0.00000000", "1.00010000", "(Float)"]],
    ];
    for (const [targetLine, [oldText, newText, fieldName]] of expectedText) {
        await contains(".o-mail-Message-trackingOld", { target: targetLine, text: oldText });
        await contains(".o-mail-Message-trackingNew", { target: targetLine, text: newText });
        await contains(".o-mail-Message-trackingField", { target: targetLine, text: fieldName });
    }
});

QUnit.test("rendering of tracked field of type integer: from non-0 to 0", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        integer_field: 1,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=integer_field] input", "0", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "10(Integer)" });
});

QUnit.test("rendering of tracked field of type integer: from 0 to non-0", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        integer_field: 0,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=integer_field] input", "1", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "01(Integer)" });
});

QUnit.test("rendering of tracked field of type monetary: from non-0 to 0", async function () {
    const pyEnv = await startServer();

    const testCurrencyId = pyEnv["res.currency"].create({ name: "ECU", symbol: "§" });
    // need to patch currencies as they're passed via cookies, not through the orm
    patchWithCleanup(currencies, {
        [testCurrencyId]: { digits: [69, 2], position: "after", symbol: "§" },
    });

    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        currency_id: testCurrencyId,
        monetary_field: 1,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=monetary_field] input", "0", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "1.00 §0.00 §(Monetary)" });
});

QUnit.test("rendering of tracked field of type monetary: from 0 to non-0", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        monetary_field: 0,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=monetary_field] input", "1", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "0.001.00(Monetary)" });
});

QUnit.test("rendering of tracked field of type boolean: from true to false", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        boolean_field: true,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    click(".o_field_boolean input").catch(() => {});
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "YesNo(Boolean)" });
});

QUnit.test("rendering of tracked field of type boolean: from false to true", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
    await this.start({ res_id: mailTestTrackAllId1 });
    click(".o_field_boolean input").catch(() => {});
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "NoYes(Boolean)" });
});

QUnit.test(
    "rendering of tracked field of type char: from a string to empty string",
    async function () {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            char_field: "Marc",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await insertText("div[name=char_field] input", "", { replace: true });
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "MarcNone(Char)" });
    }
);

QUnit.test(
    "rendering of tracked field of type char: from empty string to a string",
    async function () {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            char_field: "",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await insertText("div[name=char_field] input", "Marc", { replace: true });
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "NoneMarc(Char)" });
    }
);

QUnit.test(
    "rendering of tracked field of type date: from no date to a set date",
    async function () {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            date_field: false,
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=date_field] input"),
            "12/14/2018",
            ["change"]
        );
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "None12/14/2018(Date)" });
    }
);

QUnit.test(
    "rendering of tracked field of type date: from a set date to no date",
    async function () {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            date_field: "2018-12-14",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=date_field] input"),
            "",
            ["change"]
        );
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "12/14/2018None(Date)" });
    }
);

QUnit.test(
    "rendering of tracked field of type datetime: from no date and time to a set date and time",
    async function (assert) {
        patchTimeZone(180);
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            datetime_field: false,
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=datetime_field] input"),
            "12/14/2018 13:42:28",
            ["change"]
        );
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "None12/14/2018 13:42:28(Datetime)" });
        const savedRecord = pyEnv
            .getData()
            ["mail.test.track.all"].records.find(({ id }) => id === mailTestTrackAllId1);
        assert.strictEqual(savedRecord.datetime_field, "2018-12-14 10:42:28");
    }
);

QUnit.test(
    "rendering of tracked field of type datetime: from a set date and time to no date and time",
    async function () {
        patchTimeZone(180);
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            datetime_field: "2018-12-14 13:42:28 ",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=datetime_field] input"),
            "",
            ["change"]
        );
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "12/14/2018 16:42:28None(Datetime)" });
    }
);

QUnit.test("rendering of tracked field of type text: from some text to empty", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        text_field: "Marc",
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=text_field] textarea", "", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "MarcNone(Text)" });
});

QUnit.test("rendering of tracked field of type text: from empty to some text", async function () {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        text_field: "",
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await insertText("div[name=text_field] textarea", "Marc", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "NoneMarc(Text)" });
});

QUnit.test(
    "rendering of tracked field of type selection: from a selection to no selection",
    async function () {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            selection_field: "first",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editSelect(target, "div[name=selection_field] select", false);
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "firstNone(Selection)" });
    }
);

QUnit.test(
    "rendering of tracked field of type selection: from no selection to a selection",
    async function () {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
        await this.start({ res_id: mailTestTrackAllId1 });
        await editSelect(target, "div[name=selection_field] select", '"first"');
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "Nonefirst(Selection)" });
    }
);

QUnit.test(
    "rendering of tracked field of type many2one: from having a related record to no related record",
    async function () {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({ display_name: "Marc" });
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            many2one_field_id: resPartnerId1,
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await insertText(".o_field_many2one_selection input", "", { replace: true });
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "MarcNone(Many2one)" });
    }
);

QUnit.test(
    "rendering of tracked field of type many2one: from no related record to having a related record",
    async function () {
        const pyEnv = await startServer();
        pyEnv["res.partner"].create({ display_name: "Marc" });
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
        await this.start({ res_id: mailTestTrackAllId1 });
        await selectDropdownItem(target, "many2one_field_id", "Marc");
        await click(".o_form_button_save");
        await contains(".o-mail-Message-tracking", { text: "NoneMarc(Many2one)" });
    }
);
