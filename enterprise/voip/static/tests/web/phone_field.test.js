import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { tick } from "@odoo/hoot-mock";
import {
    click,
    contains,
    openFormView,
    registerArchs,
    start,
    startServer,
} from "@mail/../tests/mail_test_helpers";
import { setupVoipTests } from "@voip/../tests/voip_test_helpers";
import { Fake } from "@voip/../tests/mock_server/mock_models/fake";
import { defineModels } from "@web/../tests/web_test_helpers";

describe.current.tags("desktop");
setupVoipTests();
defineModels({ Fake });

beforeEach(() => {
    registerArchs({
        "fake,false,form": `
            <form string="Fake" edit="0">
                <sheet>
                    <group>
                        <field name="phone" widget="phone"/>
                    </group>
                </sheet>
            </form>`,
    });
});

test("Click on PhoneField link triggers a call.", async (assert) => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["fake"].create({ phone: "+36 55 369 678" });
    await start();
    await openFormView("fake", fakeId);
    await click(".o_field_phone a[href='tel:+3655369678']");
    expect(pyEnv["voip.call"].search_count([["phone_number", "=", "+36 55 369 678"]])).toBe(1);
});

test("Click on PhoneField link in readonly form view does not switch the form view to edit mode.", async () => {
    const pyEnv = await startServer();
    const fakeId = pyEnv["fake"].create({ phone: "+689 312172" });
    await start();
    await openFormView("fake", fakeId);
    await click(".o_field_phone a[href='tel:+689312172']");
    await tick();
    await contains(".o_form_readonly");
});
