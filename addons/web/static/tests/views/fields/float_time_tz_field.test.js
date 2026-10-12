import { expect, test } from "@odoo/hoot";
import {
    clickSave,
    contains,
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    webModels,
} from "@web/../tests/web_test_helpers";
import { user } from "@web/core/user";

const { ResCompany, ResUsers, ResPartner } = webModels;

class Foo extends models.Model {
    qux = fields.Float();

    _records = [{ id: 5, qux: 9.1 }];
}

defineModels([Foo, ResPartner, ResCompany, ResUsers]);

// "Africa/Johannesburg" is UTC+2 all year round, so these tests don't depend on
// the date at which they are run.
function patchTimeZone() {
    patchWithCleanup(user, { tz: "Africa/Johannesburg" });
}

const TZ_ARCH = `
    <form>
        <field name="qux" widget="float_time_tz" options="{ 'numeric': true }"/>
    </form>`;

test("FloatTimeTzField displays the value in the user timezone", async () => {
    patchTimeZone();
    await mountView({ type: "form", resModel: "foo", arch: TZ_ARCH, resId: 5 });

    // stored 9.1 (9:06 UTC) + 2h => 11:06
    expect(".o_field_float_time_tz[name=qux] input").toHaveValue("11:06");
});

test("FloatTimeTzField does not shift the value it just parsed", async () => {
    expect.assertions(3);
    patchTimeZone();
    onRpc("foo", "web_save", ({ args }) => {
        // the displayed 10:00 is 08:00 UTC
        expect(args[1].qux).toBe(8, {
            message: "the value should be converted back to UTC before being saved",
        });
    });

    await mountView({ type: "form", resModel: "foo", arch: TZ_ARCH, resId: 5 });

    await contains(".o_field_float_time_tz[name=qux] input").edit("10:00");
    expect(".o_field_float_time_tz[name=qux] input").toHaveValue("10:00", {
        message: "the value entered by the user should not be offset again on re-render",
    });

    await clickSave();
    expect(".o_field_float_time_tz[name=qux] input").toHaveValue("10:00", {
        message: "the saved value should be displayed back in the user timezone",
    });
});

test("FloatTimeTzField wraps around midnight", async () => {
    expect.assertions(2);
    patchTimeZone();
    onRpc("foo", "web_save", ({ args }) => {
        // 01:00 in UTC+2 is 23:00 UTC on the previous day
        expect(args[1].qux).toBe(23, {
            message: "the value should wrap around instead of becoming negative",
        });
    });

    await mountView({ type: "form", resModel: "foo", arch: TZ_ARCH, resId: 5 });

    await contains(".o_field_float_time_tz[name=qux] input").edit("01:00");
    await clickSave();
    expect(".o_field_float_time_tz[name=qux] input").toHaveValue("1:00");
});
