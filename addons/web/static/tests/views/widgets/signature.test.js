import { NameAndSignature } from "@web/core/signature/name_and_signature";
import { SignatureWidget } from "@web/views/widgets/signature/signature";

import {
    defineModels,
    fields,
    models,
    mountView,
    onRpc,
    patchWithCleanup,
    contains,
    clickModalButton,
} from "@web/../tests/web_test_helpers";
import { beforeEach, test, expect } from "@odoo/hoot";
import { click, queryFirst, waitFor } from "@odoo/hoot-dom";
import { animationFrame } from "@odoo/hoot-mock";

class Partner extends models.Model {
    display_name = fields.Char();
    product_id = fields.Many2one({ string: "Product Name", relation: "product" });
    sign = fields.Binary({ string: "Signature" });
    signature = fields.Char();

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
    onRpc("/web/sign/get_fonts/", () => ({}));
});

test.tags("desktop");
test("Signature widget renders a Sign button on desktop", async () => {
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
    await click(".o_widget_signature button.o_sign_button");
    await waitFor(".modal .modal-body");
    expect(".modal-dialog").toHaveCount(1, {
        message: "Should have one modal opened",
    });
});

test.tags("mobile");
test("Signature widget renders a Sign button on mobile", async () => {
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

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
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
    await click(".o_widget_signature button.o_sign_button");
    await waitFor(".modal .modal-body");
    expect(".modal-dialog").toHaveCount(1, {
        message: "Should have one modal opened",
    });
});

test.tags("desktop");
test("Signature widget: full_name option on desktop", async () => {
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
    await click("span.o_sign_label");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(1);
    expect.verifySteps(["Pop's Chock'lit"]);
});

test.tags("mobile");
test("Signature widget: full_name option on mobile", async () => {
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

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    // Clicks on the sign button to open the sign modal.
    await click("span.o_sign_label");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(1);
    expect.verifySteps(["Pop's Chock'lit"]);
});

test.tags("desktop");
test("Signature widget: highlight option on desktop", async () => {
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
    await click(".o_widget_signature button.o_sign_button");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(0);
});

test.tags("mobile");
test("Signature widget: highlight option on mobile", async () => {
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

    await contains(`.o_cp_action_menus button:has(.fa-cog)`).click();
    expect("button.o_sign_button").toHaveClass("btn-primary", {
        message: `The button must have the 'btn-primary' class as "highlight=1"`,
    });

    // Clicks on the sign button to open the sign modal.
    await click(".o_widget_signature button.o_sign_button");
    await waitFor(".modal .modal-body");
    expect(".modal .modal-body a.o_web_sign_auto_button").toHaveCount(0);
});

test.tags("mobile");
test("Signature widget works inside of a dropdown", async () => {
    patchWithCleanup(SignatureWidget.prototype, {
        async onClickSignature() {
            await super.onClickSignature(...arguments);
            expect.step("onClickSignature");
        },
        async uploadSignature({ signatureImage }) {
            await super.uploadSignature(...arguments);
            expect.step("uploadSignature");
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <header>
                        <button string="Dummy"/>
                        <widget name="signature" string="Sign" full_name="display_name"/>
                    </header>
                    <field name="display_name" />
                </form>
            `,
    });

    // change display_name to enable auto-sign feature
    await contains(".o_field_widget[name=display_name] input").edit("test");

    // open the signature dialog
    await contains(".o_statusbar_buttons button:has(.oi-ellipsis-v").click();
    await contains(".o_widget_signature button.o_sign_button").click();
    await waitFor(".modal .modal-body");

    // use auto-sign feature, might take a while
    await contains(".o_web_sign_auto_button").click();

    expect(".modal-footer button.btn-primary").toHaveCount(1);

    let maxDelay = 100;
    while (queryFirst(".modal-footer button.btn-primary")["disabled"] && maxDelay > 0) {
        await animationFrame();
        maxDelay--;
    }

    expect(maxDelay).toBeGreaterThan(0, { message: "Timeout exceeded" });

    // close the dialog and save the signature
    await clickModalButton({ text: "Adopt & Sign" });

    expect(".modal-dialog").toHaveCount(0, { message: "Should have no modal opened" });
    expect.verifySteps(["onClickSignature", "uploadSignature"]);
});
