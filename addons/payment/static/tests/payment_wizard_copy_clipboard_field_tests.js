/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { click, getFixture, patchWithCleanup, editInput } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Payment", {
    beforeEach() {
        target = getFixture();
        serverData = {
            models: {
                "payment.link.wizard": {
                    fields: {
                        amount: { string: "Amount", type: "float" },
                        link: { string: "Payment Link", type: "char" },
                    },
                    onchanges: {
                        amount(record) {
                            record.link = `/payment/pay?amount=${record.amount}`;
                        },
                    },
                    records: [{ id: 1, amount: 15, link: "/payment/pay?amount=15" }],
                },
            },
        };

        setupViewRegistries();
    },
});

QUnit.test("copy link immediatly after entering the amount", async (assert) => {
    assert.expect(3);

    await makeView({
        serverData,
        type: "form",
        resModel: "payment.link.wizard",
        arch: `<form>
            <group>
                <group>
                    <field name="amount"/>
                     <field
                        string="Generate and Copy Payment Link"
                        name="link"
                        widget="PaymentWizardCopyClipboardButtonField"
                    />
                </group>
            </group>
        </form>`,
        resId: 1,
        async mockRPC(route, { method, model }) {},
    });

    patchWithCleanup(browser, {
        navigator: {
            clipboard: {
                writeText: (text) => {
                    assert.step(`copied "${text}"`);
                    return Promise.resolve();
                },
            },
        },
    });

    assert.strictEqual(
        target.querySelector(".o_clipboard_button").textContent,
        "Generate and Copy Payment Link",
        "The clipboard button should show the correct label"
    );
    // not awaiting the events
    editInput(target, ".o_field_widget[name=amount] input", "13");

    await click(target, ".o_clipboard_button");
    assert.verifySteps(['copied "/payment/pay?amount=13"']);
});
