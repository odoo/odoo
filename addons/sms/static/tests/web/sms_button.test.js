import { editInput, startServer } from "@mail/../tests/mail_test_helpers";
import { beforeEach, expect, test } from "@odoo/hoot";
import { click, queryFirst } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";
import { hasTouch } from "@web/core/browser/feature_detection";
import { defineSMSModels } from "@sms/../tests/sms_test_helpers";
import { contains, MockServer, mockService, mountView } from "@web/../tests/web_test_helpers";

defineSMSModels();

async function checkSmsButton(count, isReadonly) {
    const hasDropdown = hasTouch() && !isReadonly
    if (hasDropdown) {
        await contains(".o_field_phone .o_input").click();
        await contains(".o_field_phone .o_input_box_overlay_end.dropdown-toggle").click();
    }
    if (count !== undefined) {
        expect("i.fa-mobile").toHaveCount(count);
    }
    return queryFirst(hasDropdown ? ".o_bottom_sheet .dropdown-item:contains(SMS)" : ".o_field_phone button[data-tooltip='SMS']");
}

beforeEach(async () => {
    const pyEnv = await startServer();
    pyEnv["partner"].create([
        { message: "", foo: "yop", mobile: "+32494444444" },
        { message: "", foo: "bayou" },
    ]);
    pyEnv["visitor"].create({ mobile: "+32494444444" });
});

test("Sms button in form view", async () => {
    const visitorId = MockServer.env["visitor"].search([["mobile", "=", "+32494444444"]])[0];
    await mountView({
        type: "form",
        resModel: "visitor",
        resId: visitorId,
        readonly: true,
        arch: `
            <form>
                <sheet>
                    <field name="mobile" widget="phone"/>
                </sheet>
            </form>`,
    });
    expect(".o_field_phone").toHaveCount(1);
    await checkSmsButton(1, true);
});

test("Sms button with option enable_sms set as False", async () => {
    const visitorId = MockServer.env["visitor"].search([["mobile", "=", "+32494444444"]])[0];
    await mountView({
        type: "form",
        resModel: "visitor",
        resId: visitorId,
        readonly: true,
        arch: `
            <form>
                <sheet>
                    <field name="mobile" widget="phone" options="{'enable_sms': false}"/>
                </sheet>
            </form>`,
    });
    expect(".o_field_phone").toHaveCount(1);
    await checkSmsButton(0, true);
});

test("click on the sms button while creating a new record in a FormView", async () => {
    mockService("action", {
        doAction(action, options) {
            expect.step("do_action");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.res_model).toBe("sms.composer");
            options.onClose();
        },
    });
    const partnerId = MockServer.env["partner"].search([["foo", "=", "yop"]])[0];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: partnerId,
        arch: `
            <form>
                <sheet>
                    <field name="foo"/>
                    <field name="mobile" widget="phone"/>
                </sheet>
            </form>`,
    });
    await editInput(document.body, "[name='foo'] input", "John");
    await editInput(document.body, "[name='mobile'] input", "+32494444411");
    const smsButton = await checkSmsButton(1);
    await click(smsButton);
    expect("[name='foo'] input:first").toHaveValue("John");
    expect("[name='mobile'] input:first").toHaveValue("+32494444411");
    await expect.waitForSteps(["do_action"]);
});

test("click on the sms button in a FormViewDialog has no effect on the main form view", async () => {
    mockService("action", {
        doAction(action, options) {
            expect.step("do_action");
            expect(action.type).toBe("ir.actions.act_window");
            expect(action.res_model).toBe("sms.composer");
            options.onClose();
        },
    });
    const partnerId = MockServer.env["partner"].search([["foo", "=", "yop"]])[0];
    await mountView({
        type: "form",
        resModel: "partner",
        resId: partnerId,
        arch: `
            <form>
                <sheet>
                    <field name="foo"/>
                    <field name="mobile" widget="phone"/>
                    <field name="partner_ids">
                    <kanban>
                        <templates>
                            <t t-name="card">
                                <field name="display_name"/>
                            </t>
                        </templates>
                    </kanban>
                </field>
                </sheet>
            </form>`,
    });

    await editInput(document.body, "[name='foo'] input", "John");
    await editInput(document.body, "[name='mobile'] input", "+32494444411");
    await click(".o-kanban-button-new");
    await animationFrame();
    await editInput(document.body, ".modal .o_field_char[name='foo'] input", "Max");
    await editInput(document.body, ".modal .o_field_phone[name='mobile'] input", "+324955555");
    const smsButton = await checkSmsButton();
    await click(smsButton);
    expect(".modal [name='foo'] input:first").toHaveValue("Max");
    expect(".modal [name='mobile'] input:first").toHaveValue("+324955555");

    await click(":nth-child(1 of .modal) .o_form_button_cancel");
    expect("[name='foo'] input:first").toHaveValue("John");
    expect("[name='mobile'] input:first").toHaveValue("+32494444411");
    await expect.waitForSteps(["do_action"]);
});
