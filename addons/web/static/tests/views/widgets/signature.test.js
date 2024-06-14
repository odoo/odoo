import { NameAndSignature } from "@web/core/signature/name_and_signature";

import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
} from "@web/../tests/web_test_helpers";
import { beforeEach, test, expect } from "@odoo/hoot";
import { click, waitFor } from "@odoo/hoot-dom";

class Partner extends models.Model {
    display_name = fields.Char({ string: "Name" });
    product_id = fields.Many2one({ string: "Product Name", relation: "product" });
    sign = fields.Binary({ string: "Signature" });
    _records = [
        {
            id: 1,
            display_name: "Pop's Chock'lit",
            product_id: 7,
        },
    ];
}

class Product extends models.Model {
    name = fields.Char({ string: "Product Name" });
    _records = [
        {
            id: 7,
            name: "Veggie Burger",
        },
    ];
}

defineModels([Partner, Product]);

beforeEach(async () => {
    onRpc("/web/sign/get_fonts/", () => {
        return {};
    });
});

test("Signature widget renders a Sign button", async () => {
    patchWithCleanup(NameAndSignature.prototype, {
        setup() {
            super.setup();
            expect(this.props.signature.name).toBe("");
        },
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
        <form>
            <header>
                <widget name="signature" string="Sign"/>
            </header>
        </form>`,
    });

    expect("button.o_sign_button").toHaveClass("btn-secondary", {
        message: `The button must have the 'btn-secondary' class as "highlight=0"`,
    });
    expect(".o_widget_signature button.o_sign_button").toHaveCount(1, {
        message: "Should have a signature widget button",
    });
    expect(".modal-dialog").toHaveCount(0, {
        message: "Should not have any modal",
    });
    // Clicks on the sign button to open the sign modal.
    click(".o_widget_signature button.o_sign_button");
    await waitFor(".modal .modal-body");
    expect(".modal-dialog").toHaveCount(1, {
        message: "Should have one modal opened",
    });
});

test("Signature widget: full_name option", async () => {
    patchWithCleanup(NameAndSignature.prototype, {
        setup() {
            super.setup();
            expect.step(this.props.signature.name);
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
        <form>
            <header>
                <widget name="signature" string="Sign" full_name="display_name"/>
            </header>
            <field name="display_name"/>
        </form>`,
    });
    // Clicks on the sign button to open the sign modal.
    click("span.o_sign_label");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(1);
    expect(["Pop's Chock'lit"]).toVerifySteps();
});

test("Signature widget: highlight option", async () => {
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
        <form>
            <header>
                <widget name="signature" string="Sign" highlight="1"/>
            </header>
        </form>`,
    });

    expect("button.o_sign_button").toHaveClass("btn-primary", {
        message: `The button must have the 'btn-primary' class as "highlight=1"`,
    });

    // Clicks on the sign button to open the sign modal.
    click(".o_widget_signature button.o_sign_button");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(0);
});
