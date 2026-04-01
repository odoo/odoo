import {
    contains,
    click,
    insertText,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { mockDate, mockTimeZone } from "@odoo/hoot-mock";
import { defineTestMailModels } from "@test_mail/../tests/test_mail_test_helpers";
import { editSelectMenu, patchWithCleanup } from "@web/../tests/web_test_helpers";
import { currencies } from "@web/core/currency";

const archs = {
    "mail.test.track.all,false,form": `
        <form>
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
            <chatter/>
        </form>
    `,
};

describe.current.tags("desktop");
defineTestMailModels();
beforeEach(() => mockTimeZone(0));

test("basic rendering of tracking value (float type)", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({ float_field: 12.3 });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
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

test("rendering of tracked field of type float: from non-0 to 0", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        float_field: 1,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=float_field] input", "0", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "1.000.00(Float)" });
});

test("rendering of tracked field of type float: from 0 to non-0", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        float_field: 0,
        float_field_with_digits: 0,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=float_field] input", "1.01", { replace: true });
    await insertText("div[name=float_field_with_digits] input", "1.0001", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { count: 2 });
    const [increasedPrecisionLine, defaultPrecisionLine] =
        document.getElementsByClassName("o-mail-Message-tracking");
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

test("rendering of tracked field of type integer: from non-0 to 0", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        integer_field: 1,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=integer_field] input", "0", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "10(Integer)" });
});

test("rendering of tracked field of type integer: from 0 to non-0", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        integer_field: 0,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=integer_field] input", "1", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "01(Integer)" });
});

test("rendering of tracked field of type monetary: from non-0 to 0", async () => {
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
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=monetary_field] input", "0", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "1.00 §0.00 §(Monetary)" });
});

test("rendering of tracked field of type monetary: from 0 to non-0", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        monetary_field: 0,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=monetary_field] input", "1", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "0.001.00(Monetary)" });
});

test("rendering of tracked field of type boolean: from true to false", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        boolean_field: true,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click(".o_field_boolean input");
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "YesNo(Boolean)" });
});

test("rendering of tracked field of type boolean: from false to true", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click(".o_field_boolean input");
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "NoYes(Boolean)" });
});

test("rendering of tracked field of type char: from a string to empty string", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        char_field: "Marc",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=char_field] input", "", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "MarcNone(Char)" });
});

test("rendering of tracked field of type char: from empty string to a string", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        char_field: "",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=char_field] input", "Marc", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "NoneMarc(Char)" });
});

test("rendering of tracked field of type date: from no date to a set date", async () => {
    mockDate("2018-12-01");
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        date_field: false,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click("div[name=date_field] input");
    await click(".o_datetime_button", { text: "14" });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "None12/14/2018(Date)" });
});

test("rendering of tracked field of type date: from a set date to no date", async () => {
    mockDate("2018-12-01");
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        date_field: "2018-12-14",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click("div[name=date_field] button");
    await insertText("div[name=date_field] input", "", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "12/14/2018None(Date)" });
});

test("rendering of tracked field of type datetime: from no date and time to a set date and time", async function () {
    mockDate("2018-12-01", 3);
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        datetime_field: false,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click("div[name=datetime_field] input");
    await click(".o_datetime_button", { text: "14" });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "None12/14/2018 12:00:00(Datetime)" });
    const [savedRecord] = pyEnv["mail.test.track.all"].search_read([
        ["id", "=", mailTestTrackAllId1],
    ]);
    expect(savedRecord.datetime_field).toBe("2018-12-14 09:00:00");
});

test("rendering of tracked field of type datetime: from a set date and time to no date and time", async () => {
    mockTimeZone(3);
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        datetime_field: "2018-12-14 13:42:28 ",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click("div[name=datetime_field] button");
    await insertText("div[name=datetime_field] input", "", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "12/14/2018 16:42:28None(Datetime)" });
});

test("rendering of tracked field of type text: from some text to empty", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        text_field: "Marc",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=text_field] textarea", "", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "MarcNone(Text)" });
});

test("rendering of tracked field of type text: from empty to some text", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        text_field: "",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText("div[name=text_field] textarea", "Marc", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "NoneMarc(Text)" });
});

test("rendering of tracked field of type selection: from a selection to no selection", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        selection_field: "first",
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await editSelectMenu("div[name=selection_field] input", { value: "" });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "firstNone(Selection)" });
});

test("rendering of tracked field of type selection: from no selection to a selection", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await editSelectMenu("div[name=selection_field] input", { value: "First" });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "Nonefirst(Selection)" });
});

test("rendering of tracked field of type many2one: from having a related record to no related record", async () => {
    const pyEnv = await startServer();
    const resPartnerId1 = pyEnv["res.partner"].create({ name: "Marc" });
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        many2one_field_id: resPartnerId1,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await insertText(".o_field_many2one_selection input", "", { replace: true });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "MarcNone(Many2one)" });
});

test("rendering of tracked field of type many2one: from no related record to having a related record", async () => {
    const pyEnv = await startServer();
    pyEnv["res.partner"].create({ name: "Marc" });
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId1);
    await click("[name=many2one_field_id] input");
    await click("[name=many2one_field_id] .o-autocomplete--dropdown-item", { text: "Marc" });
    await click(".o_form_button_save");
    await contains(".o-mail-Message-tracking", { text: "NoneMarc(Many2one)" });
});

test("Search message with filter in chatter", async () => {
    const pyEnv = await startServer();
    const mailTestTrackAllId = pyEnv["mail.test.track.all"].create({});
    pyEnv["mail.message"].create({
        body: "Hermit",
        model: "mail.test.track.all",
        res_id: mailTestTrackAllId,
    });
    await start();
    registerArchs(archs);
    await openFormView("mail.test.track.all", mailTestTrackAllId);
    await click("[name=many2one_field_id] input");
    await click("[name=many2one_field_id] .o-autocomplete--dropdown-item", { text: "Hermit" });
    await click(".o_form_button_save");
    // Search message with filter
    await click("[title='Search Messages']");
    await insertText(".o_searchview_input", "Hermit");
    await click("button[title='Filter Messages']");
    await click("span", { text: "Conversations" });
    await contains(".o-mail-SearchMessageResult .o-mail-Message", { text: "Hermit" });

    await click("button[title='Filter Messages']");
    await click("span", { text: "Tracked Changes" });
    await contains(".o-mail-SearchMessageResult .o-mail-Message", { text: "Hermit" });

    await click("button[title='Filter Messages']");
    await click("span", { text: "All" });
    await contains(".o-mail-SearchMessageResult .o-mail-Message", { count: 2 });
});
