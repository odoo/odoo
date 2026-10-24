import { expect, runAllTimers, test, waitFor, waitForNone } from "@odoo/hoot";
import {
    clickSave,
    defineModels,
    fieldInput,
    fields,
    models,
    mountView,
    onRpc,
} from "@web/../tests/web_test_helpers";

class Bank extends models.Model {
    account_number = fields.Char();

    _records = [{ id: 1, account_number: "" }];
}

defineModels([Bank]);

const VALID_IBAN = "BE12651194580992";
const VALID_CLABE = "002010077777777771";
const INVALID_ACCOUNT_NUMBER = "invalidAccountNumber!";

test.tags("focus required");
test("Account Number Widget full flow", async () => {
    let callCount = 0;
    onRpc("retrieve_account_type", ({ args }) => {
        callCount++;
        switch (args[0].replace(/\s/g, "")) {
            case VALID_IBAN:
                return "iban";
            case VALID_CLABE:
                return "clabe";
            default:
                return "bank";
        }
    });
    await mountView({
        type: "form",
        resModel: "bank",
        resId: 1,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="account_number" widget="account_number"/>
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_widget[name='account_number'] input").toHaveCount(1);
    expect(".o_account_number").toHaveCount(0, {
        message: "no badge for an empty account number",
    });

    // Too short to match any format: not worth a round-trip to the server.
    await fieldInput("account_number").edit("BE12", { confirm: false });
    await runAllTimers();
    expect(".o_account_number").toHaveCount(0);
    expect(callCount).toBe(0, {
        message: "a number shorter than the shortest IBAN is never sent to the server",
    });

    // An invalid number never gets a badge, whether saved or not.
    await fieldInput("account_number").edit(INVALID_ACCOUNT_NUMBER, { confirm: false });
    expect(".o_account_number").toHaveCount(0, {
        message: "the badge does not change before the debounce elapses",
    });
    await runAllTimers();
    expect(".o_account_number").toHaveCount(0, {
        message: "no badge for an invalid account number",
    });
    await clickSave();
    await runAllTimers();
    expect(".o_account_number").toHaveCount(0, {
        message: "no badge for an invalid account number, even once saved",
    });

    // A valid IBAN gets one, but only once the debounce has elapsed.
    await fieldInput("account_number").edit(VALID_IBAN, { confirm: false });
    expect(".o_account_number").toHaveCount(0, {
        message: "the badge does not change before the debounce elapses",
    });
    await runAllTimers();
    await waitFor(".o_account_number i[data-icon='check']");

    // ... and keeps it once the field is no longer being edited.
    await clickSave();
    await runAllTimers();
    await waitFor(".o_account_number");

    // Going back to an invalid number drops the badge again.
    await fieldInput("account_number").edit(INVALID_ACCOUNT_NUMBER, { confirm: false });
    await runAllTimers();
    await waitForNone(".o_account_number");

    // CLABE numbers are recognised too.
    await fieldInput("account_number").edit(VALID_CLABE, { confirm: false });
    await runAllTimers();
    await waitFor(".o_account_number");
});
