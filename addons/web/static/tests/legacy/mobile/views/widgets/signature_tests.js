/** @odoo-module alias=@web/../tests/mobile/views/widgets/signature_tests default=false */
import { click, getFixture, patchWithCleanup, editInput, nextTick } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { SignatureWidget } from "@web/views/widgets/signature/signature";

let serverData;
let target;

QUnit.module("Widgets", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Name", type: "char" },
                        product_id: {
                            string: "Product Name",
                            type: "many2one",
                            relation: "product",
                        },
                        signature: { string: "", type: "string" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "Pop's Chock'lit",
                            product_id: 7,
                        },
                    ],
                    onchanges: {},
                },
                product: {
                    fields: {
                        name: { string: "Product Name", type: "char" },
                    },
                    records: [
                        {
                            id: 7,
                            display_name: "Veggie Burger",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("Signature Widget");

    QUnit.test("Signature widget works inside of a dropdown", async (assert) => {
        assert.expect(7);
        patchWithCleanup(SignatureWidget.prototype, {
            async onClickSignature() {
                await super.onClickSignature(...arguments);
                assert.step("onClickSignature");
            },
            async uploadSignature({signatureImage}) {
                await super.uploadSignature(...arguments);
                assert.step("uploadSignature");
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <button string="Dummy"/>
                        <widget name="signature" string="Sign" full_name="display_name"/>
                    </header>
                    <field name="display_name" />
                </form>
            `,
            mockRPC: async (route, args) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        // change display_name to enable auto-sign feature
        await editInput(target, ".o_field_widget[name=display_name] input", "test");

        // open the signature dialog
        await click(target, ".o_cp_action_menus button:has(.fa-cog)");
        await click(target, ".o_widget_signature button.o_sign_button");

        assert.containsOnce(target, ".modal-dialog", "Should have one modal opened");

        // use auto-sign feature, might take a while
        await click(target, ".o_web_sign_auto_button");

        assert.containsOnce(target, ".modal-footer button.btn-primary");

        let maxDelay = 100;
        while (target.querySelector(".modal-footer button.btn-primary")["disabled"] && maxDelay > 0) {
            await nextTick();
            maxDelay--;
        }

        assert.equal(maxDelay > 0, true, "Timeout exceeded");

        // close the dialog and save the signature
        await click(target, ".modal-footer button.btn-primary:enabled");

        assert.containsNone(target, ".modal-dialog", "Should have no modal opened");

        assert.verifySteps(["onClickSignature", "uploadSignature"], "An error has occurred while signing");
    });
});
