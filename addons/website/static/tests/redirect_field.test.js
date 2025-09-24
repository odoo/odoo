import { expect, test, describe } from "@odoo/hoot";
import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    contains,
} from "@web/../tests/web_test_helpers";
import { defineMailModels } from "@mail/../tests/mail_test_helpers";

class Appointment extends models.Model {
    _name = "appointment";

    is_published = fields.Boolean({ searchable: true, trim: true });

    _records = [
        {
            is_published: true,
        },
        {
            is_published: false,
        },
    ];

    _views = {
        form: `
            <form>
                <sheet>
                    <div class="oe_button_box" name="button_box">
                        <field name="is_published" widget="website_redirect_button" />
                    </div>
                </sheet>
            </form>`,
    };
}

defineModels([Appointment]);
defineMailModels();

describe.current.tags("desktop");

test("redirect field in form view is green if value=true", async () => {
    await mountView({
        type: "form",
        resModel: "appointment",
        resId: 1,
    });

    expect(".oe_stat_button .o_button_icon.text-success").toHaveCount(1);
});

test("clicking on redirect field works", async () => {
    onRpc("appointment", "open_website_url", () => {
        expect.step("Call Open Website Url");
        return true;
    });

    await mountView({
        type: "form",
        resModel: "appointment",
        resId: 1,
    });

    await contains(".oe_stat_button").click();
    expect.verifySteps(["Call Open Website Url"]);
});

test("redirect field in form view is red if value=false", async () => {
    await mountView({
        type: "form",
        resModel: "appointment",
        resId: 2,
    });

    expect(".oe_stat_button .o_button_icon.text-danger").toHaveCount(1);
});
