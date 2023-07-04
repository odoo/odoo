/** @odoo-module **/
import {
    click,
    getFixture,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    triggerEvents,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
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

    QUnit.module("Signature Field");

    QUnit.test("signature can be drawn", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                        <field name="sign" widget="signature" />
                    </form>`,
            mockRPC: async (route) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        assert.containsNone(target, "div[name=sign] img.o_signature");
        assert.containsOnce(
            target,
            "div[name=sign] div.o_signature svg",
            "should have a valid signature widget"
        );

        // Click on the widget to open signature modal
        await click(target, "div[name=sign] div.o_signature");
        assert.containsOnce(target, ".modal .modal-body .o_web_sign_name_and_signature");
        assert.containsNone(target, ".modal .btn.btn-primary:not([disabled])");

        // Use a drag&drop simulation to draw a signature
        const def = makeDeferred();
        const jSignatureEl = target.querySelector(".modal .o_web_sign_signature");
        $(jSignatureEl).on("change", def.resolve);
        const { x, y, width, height } = target
            .querySelector("canvas.jSignature")
            .getBoundingClientRect();
        await triggerEvents(jSignatureEl, "canvas.jSignature", [
            ["mousedown", { clientX: x + 1, clientY: y + 1 }],
            ["mousemove", { clientX: x + width - 1, clientY: height + height - 1 }],
            ["mouseup", { clientX: x + width - 1, clientY: height + height - 1 }],
        ]);
        await def; // makes sure the signature stroke is taken into account by jSignature
        await nextTick(); // await owl rendering
        assert.containsOnce(target, ".modal .btn.btn-primary:not([disabled])");

        // Click on "Adopt and Sign" button
        await click(target, ".modal .btn.btn-primary:not([disabled])");
        assert.containsNone(target, ".modal");

        // The signature widget should now display the signature img
        assert.containsNone(target, "div[name=sign] div.o_signature svg");
        assert.containsOnce(target, "div[name=sign] img.o_signature");

        const signImgSrc = target.querySelector("div[name=sign] img.o_signature").dataset.src;
        assert.notOk(signImgSrc.includes("placeholder"));
        assert.ok(signImgSrc.startsWith("data:image/png;base64,"));
    });

    QUnit.test("Set simple field in 'full_name' node option", async function (assert) {
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
                        <field name="display_name"/>
                        <field name="sign" widget="signature" options="{'full_name': 'display_name'}" />
                    </form>`,
            mockRPC: async (route) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        assert.containsOnce(
            target,
            "div[name=sign] div.o_signature svg",
            "should have a valid signature widget"
        );
        // Click on the widget to open signature modal
        await click(target, "div[name=sign] div.o_signature");
        assert.containsOnce(
            target,
            ".modal .modal-body a.o_web_sign_auto_button",
            'should open a modal with "Auto" button'
        );
        assert.hasClass(
            target.querySelector(".o_web_sign_auto_button"),
            "active",
            "'Auto' panel is visible by default"
        );
        assert.verifySteps(["Pop's Chock'lit"]);
    });

    QUnit.test("Set m2o field in 'full_name' node option", async function (assert) {
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
                    <field name="product_id"/>
                    <field name="sign" widget="signature" options="{'full_name': 'product_id'}" />
                </form>`,
            mockRPC: async (route) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        assert.containsOnce(
            target,
            "div[name=sign] div.o_signature svg",
            "should have a valid signature widget"
        );

        // Click on the widget to open signature modal
        await click(target, "div[name=sign] div.o_signature");
        assert.containsOnce(
            target,
            ".modal .modal-body a.o_web_sign_auto_button",
            'should open a modal with "Auto" button'
        );
        assert.verifySteps(["Veggie Burger"]);
    });

    QUnit.test("Set size (width and height) in node option", async function (assert) {
        serverData.models.partner.fields.sign2 = { string: "Signature", type: "binary" };
        serverData.models.partner.fields.sign3 = { string: "Signature", type: "binary" };

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                        <field name="sign" widget="signature" options="{'size': [150,'']}" />
                        <field name="sign2" widget="signature" options="{'size': ['',100]}" />
                        <field name="sign3" widget="signature" options="{'size': [120,130]}" />
                    </form>`,
            mockRPC: async (route) => {
                if (route === "/web/sign/get_fonts/") {
                    return {};
                }
            },
        });

        assert.containsN(target, ".o_signature", 3);

        const sign = target.querySelector("[name='sign'] .o_signature");
        assert.strictEqual(sign.style.width, "150px");
        assert.strictEqual(sign.style.height, "50px");

        const sign2 = target.querySelector("[name='sign2'] .o_signature");
        assert.strictEqual(sign2.style.width, "300px");
        assert.strictEqual(sign2.style.height, "100px");

        const sign3 = target.querySelector("[name='sign3'] .o_signature");
        assert.strictEqual(sign3.style.width, "120px");
        assert.strictEqual(sign3.style.height, "40px");
    });
});
