/* @odoo-module */

import { startServer } from "@bus/../tests/helpers/mock_python_environment";
import { addFakeModel } from "@bus/../tests/helpers/model_definitions_helpers";

import { start } from "@mail/../tests/helpers/test_utils";

import { click, contains } from "@web/../tests/utils";
import { nextTick } from "@web/../tests/helpers/utils";

const views = {
    "fake,false,form": `
        <form string="Fake" edit="0">
            <sheet>
                <group>
                    <field name="phone" widget="phone"/>
                </group>
            </sheet>
        </form>`,
};

addFakeModel("fake", { phone: { string: "Phone Number", type: "char" } });

QUnit.module("phone field");

QUnit.test("Click on PhoneField link triggers a call.", async (assert) => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["fake"].create({ phone: "+36 55 369 678" });
    const { openFormView } = await start({ serverData: { views } });
    openFormView("fake", fakeId, {
        waitUntilDataLoaded: false,
        waitUntilMessagesLoaded: false,
    });
    await click(".o_field_phone a[href='tel:+3655369678']");
    assert.strictEqual(
        pyEnv["voip.call"].searchCount([["phone_number", "=", "+36 55 369 678"]]),
        1
    );
});

QUnit.test(
    "Click on PhoneField link in readonly form view does not switch the form view to edit mode.",
    async () => {
        const pyEnv = await startServer();
        const fakeId = pyEnv["fake"].create({ phone: "+689 312172" });
        const { openFormView } = await start({ serverData: { views } });
        openFormView("fake", fakeId, {
            waitUntilDataLoaded: false,
            waitUntilMessagesLoaded: false,
        });
        await click(".o_field_phone a[href='tel:+689312172']");
        await nextTick();
        await contains(".o_form_readonly");
    }
);
