/** @odoo-module **/

import { click, start, startServer } from "@mail/../tests/helpers/test_utils";

import {
    editInput,
    editSelect,
    selectDropdownItem,
    patchWithCleanup,
    patchTimeZone,
    getFixture,
} from "@web/../tests/helpers/utils";

import session from "web.session";
import testUtils from "web.test_utils";

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

        patchWithCleanup(session, {
            getTZOffset() {
                return 0;
            },
        });
    },
});

QUnit.test("basic rendering of tracking value (float type)", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({ float_field: 12.3 });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=float_field] input", 45.67);
    await click(".o_form_button_save");
    assert.containsOnce(target, ".o-Message-tracking");
    assert.containsOnce(target, ".o-Message-trackingField");
    assert.strictEqual(
        target.querySelector(".o-Message-trackingField").textContent,
        "(Float)"
    );
    assert.containsOnce(target, ".o-Message-trackingOld");
    assert.strictEqual(target.querySelector(".o-Message-trackingOld").textContent, "12.30");
    assert.containsOnce(target, ".o-Message-trackingSeparator");
    assert.containsOnce(target, ".o-Message-trackingNew");
    assert.strictEqual(target.querySelector(".o-Message-trackingNew").textContent, "45.67");
});

QUnit.test("rendering of tracked field of type float: from non-0 to 0", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        float_field: 1,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=float_field] input", 0);
    await click(".o_form_button_save");
    assert.strictEqual(
        target.querySelector(".o-Message-tracking").textContent,
        "1.000.00(Float)"
    );
});

QUnit.test("rendering of tracked field of type float: from 0 to non-0", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        float_field: 0,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=float_field] input", 1);
    await click(".o_form_button_save");
    assert.strictEqual(
        target.querySelector(".o-Message-tracking").textContent,
        "0.001.00(Float)"
    );
});

QUnit.test("rendering of tracked field of type integer: from non-0 to 0", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        integer_field: 1,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=integer_field] input", 0);
    await click(".o_form_button_save");
    assert.strictEqual(target.querySelector(".o-Message-tracking").textContent, "10(Integer)");
});

QUnit.test("rendering of tracked field of type integer: from 0 to non-0", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        integer_field: 0,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=integer_field] input", 1);
    await click(".o_form_button_save");
    assert.strictEqual(target.querySelector(".o-Message-tracking").textContent, "01(Integer)");
});

QUnit.test("rendering of tracked field of type monetary: from non-0 to 0", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        monetary_field: 1,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=monetary_field] input", 0);
    await click(".o_form_button_save");
    assert.strictEqual(
        target.querySelector(".o-Message-tracking").textContent,
        "1.000.00(Monetary)"
    );
});

QUnit.test("rendering of tracked field of type monetary: from 0 to non-0", async function (assert) {
    const pyEnv = await startServer();
    const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
        monetary_field: 0,
    });
    await this.start({ res_id: mailTestTrackAllId1 });
    await editInput(target, "div[name=monetary_field] input", 1);
    await click(".o_form_button_save");
    assert.strictEqual(
        target.querySelector(".o-Message-tracking").textContent,
        "0.001.00(Monetary)"
    );
});

QUnit.test(
    "rendering of tracked field of type boolean: from true to false",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            boolean_field: true,
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        click(".o_field_boolean input").catch(() => {});
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "YesNo(Boolean)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type boolean: from false to true",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
        await this.start({ res_id: mailTestTrackAllId1 });
        click(".o_field_boolean input").catch(() => {});
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "NoYes(Boolean)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type char: from a string to empty string",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            char_field: "Marc",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editInput(target, "div[name=char_field] input", "");
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "MarcNone(Char)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type char: from empty string to a string",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            char_field: "",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editInput(target, "div[name=char_field] input", "Marc");
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "NoneMarc(Char)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type date: from no date to a set date",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            date_field: false,
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=date_field] .o_datepicker .o_datepicker_input"),
            "12/14/2018",
            ["change"]
        );
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "None12/14/2018(Date)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type date: from a set date to no date",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            date_field: "2018-12-14",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=date_field] .o_datepicker .o_datepicker_input"),
            "",
            ["change"]
        );
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "12/14/2018None(Date)"
        );
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
            target.querySelector("div[name=datetime_field] .o_datepicker .o_datepicker_input"),
            "12/14/2018 13:42:28",
            ["change"]
        );
        await click(".o_form_button_save");
        const savedRecord = pyEnv
            .getData()
            ["mail.test.track.all"].records.find(({ id }) => id === mailTestTrackAllId1);
        assert.strictEqual(savedRecord.datetime_field, "2018-12-14 10:42:28");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "None12/14/2018 13:42:28(Datetime)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type datetime: from a set date and time to no date and time",
    async function (assert) {
        patchTimeZone(180);
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            datetime_field: "2018-12-14 13:42:28 ",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await testUtils.fields.editAndTrigger(
            target.querySelector("div[name=datetime_field] .o_datepicker .o_datepicker_input"),
            "",
            ["change"]
        );
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "12/14/2018 16:42:28None(Datetime)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type text: from some text to empty",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            text_field: "Marc",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editInput(target, "div[name=text_field] textarea", "");
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "MarcNone(Text)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type text: from empty to some text",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            text_field: "",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editInput(target, "div[name=text_field] textarea", "Marc");
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "NoneMarc(Text)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type selection: from a selection to no selection",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            selection_field: "first",
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editSelect(target, "div[name=selection_field] select", false);
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "firstNone(Selection)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type selection: from no selection to a selection",
    async function (assert) {
        const pyEnv = await startServer();
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
        await this.start({ res_id: mailTestTrackAllId1 });
        await editSelect(target, "div[name=selection_field] select", '"first"');
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "Nonefirst(Selection)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type many2one: from having a related record to no related record",
    async function (assert) {
        const pyEnv = await startServer();
        const resPartnerId1 = pyEnv["res.partner"].create({ display_name: "Marc" });
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({
            many2one_field_id: resPartnerId1,
        });
        await this.start({ res_id: mailTestTrackAllId1 });
        await editInput(target, ".o_field_many2one_selection input", "");
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "MarcNone(Many2one)"
        );
    }
);

QUnit.test(
    "rendering of tracked field of type many2one: from no related record to having a related record",
    async function (assert) {
        const pyEnv = await startServer();
        pyEnv["res.partner"].create({ display_name: "Marc" });
        const mailTestTrackAllId1 = pyEnv["mail.test.track.all"].create({});
        await this.start({ res_id: mailTestTrackAllId1 });
        await selectDropdownItem(target, "many2one_field_id", "Marc");
        await click(".o_form_button_save");
        assert.strictEqual(
            target.querySelector(".o-Message-tracking").textContent,
            "NoneMarc(Many2one)"
        );
    }
);
