/** @odoo-module **/
import { click, getFixture, patchWithCleanup } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

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
                        sign: { string: "Signature", type: "binary" },
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

    QUnit.test("Signature widget renders a Sign button", async function (assert) {
        assert.expect(5);

        patchWithCleanup(NameAndSignature.prototype, {
            setup() {
                super.setup(...arguments);
                assert.strictEqual(this.props.signature.name, "");
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                    <header>
                        <widget name="signature" string="Sign"/>
                    </header>
                </form>`,
            mockRPC: async (route, args) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        assert.hasClass(
            target.querySelector("button.o_sign_button"),
            "btn-secondary",
            "The button must have the 'btn-secondary' class as \"highlight=0\""
        );
        assert.containsOnce(
            target,
            ".o_widget_signature button.o_sign_button",
            "Should have a signature widget button"
        );
        assert.containsNone(target, ".modal-dialog", "Should not have any modal");

        // Clicks on the sign button to open the sign modal.
        await click(target, ".o_widget_signature button.o_sign_button");
        assert.containsOnce(target, ".modal-dialog", "Should have one modal opened");
    });

    QUnit.test("Signature widget: full_name option", async function (assert) {
        patchWithCleanup(NameAndSignature.prototype, {
            setup() {
                super.setup(...arguments);
                assert.step(this.props.signature.name);
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                        <header>
                            <widget name="signature" string="Sign" full_name="display_name"/>
                        </header>
                        <field name="display_name"/>
                    </form>`,
            mockRPC: async (route) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });
        // Clicks on the sign button to open the sign modal.
        await click(target, "span.o_sign_label");
        assert.containsOnce(target, ".modal .modal-body a.o_web_sign_auto_button");
        assert.verifySteps(["Pop's Chock'lit"]);
    });

    QUnit.test("Signature widget: highlight option", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                    <header>
                        <widget name="signature" string="Sign" highlight="1"/>
                    </header>
                </form>`,
            mockRPC: async (route, args) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        assert.hasClass(
            target.querySelector("button.o_sign_button"),
            "btn-primary",
            "The button must have the 'btn-primary' class as \"highlight=1\""
        );
        // Clicks on the sign button to open the sign modal.
        await click(target, ".o_widget_signature button.o_sign_button");
        assert.containsNone(target, ".modal .modal-body a.o_web_sign_auto_button");
    });
});
