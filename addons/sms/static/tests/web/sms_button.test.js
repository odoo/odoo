import {
    click,
    contains,
    editInput,
    startServer
} from "@mail/../tests/mail_test_helpers";
import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { defineSMSModels } from "@sms/../tests/sms_test_helpers";
import { MockServer, asyncStep, mockService, mountView, waitForSteps } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
defineSMSModels();

beforeEach(async () => {
    const pyEnv = await startServer();
    pyEnv["partner"].create([
        { message: "", foo: "yop", mobile: "+32494444444"},
        { message: "", foo: "bayou"},
    ]);
    pyEnv["visitor"].create([
        { mobile: "+32494444444" },
    ]);
})

test("Sms button in form view", async () => {
    const visitorId = MockServer.env["visitor"].search([["mobile","=","+32494444444"]])[0];
    await mountView({
        type: "form",
        resModel: "visitor",
        resId: visitorId,
        readonly: true,
        arch:
            `<form>
                <sheet>
                    <field name="mobile" widget="phone"/>
                </sheet>
            </form>`
    });
    await contains(".o_field_phone");
    await contains(".o_field_phone a.o_field_phone_sms", { count: 1 });
});

test("Sms button with option enable_sms set as False", async () => {
    const visitorId = MockServer.env["visitor"].search([["mobile","=","+32494444444"]])[0];
    await mountView({
        type: "form",
        resModel: "visitor",
        resId: visitorId,
        readonly: true,
        arch:
            `<form>
                <sheet>
                    <field name="mobile" widget="phone" options="{'enable_sms': false}"/>
                </sheet>
            </form>`
    });
    await contains(".o_field_phone");
    await contains(".o_field_phone a.o_field_phone_sms", { count: 0 });
});

test("click on the sms button while creating a new record in a FormView", async () => {
    mockService("action", {
        doAction(action, options) {
            asyncStep("do_action");
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
        arch:
            `<form>
                <sheet>
                    <field name="foo"/>
                    <field name="mobile" widget="phone"/>
                </sheet>
            </form>`,
    });
    await editInput(document.body, "[name='foo'] input", "John");
    await editInput(document.body, "[name='mobile'] input", "+32494444411");
    await click(".o_field_phone_sms");
    expect("[name='foo'] input:first").toHaveValue("John");
    expect("[name='mobile'] input:first").toHaveValue("+32494444411");
    await waitForSteps(["do_action"]);
});


test(
    "click on the sms button in a FormViewDialog has no effect on the main form view",
    async () => {
        mockService("action", {
            doAction(action, options){
                asyncStep("do_action");
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
            arch:
                `<form>
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
        await contains(".modal");

        await editInput(document.body, ".modal .o_field_char[name='foo'] input", "Max");
        await editInput(document.body, ".modal .o_field_phone[name='mobile'] input", "+324955555");
        await click(":nth-child(1 of .modal) .o_field_phone_sms");
        expect(".modal [name='foo'] input:first").toHaveValue("Max");
        expect(".modal [name='mobile'] input:first").toHaveValue("+324955555");

        await click(":nth-child(1 of .modal) .o_form_button_cancel");
        expect("[name='foo'] input:first").toHaveValue("John");
        expect("[name='mobile'] input:first").toHaveValue("+32494444411");
        await waitForSteps(["do_action"]);
    }
);
