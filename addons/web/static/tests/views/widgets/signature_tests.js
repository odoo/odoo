/** @odoo-module **/
import {
    click,
    getFixture,
    patchWithCleanup,
    triggerEvent,
    editInput,
    clickSave,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

let serverData;
let target;

function getUnique(target) {
    const src = target.dataset.src;
    return new URL(src).searchParams.get("unique");
}

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
                        __last_update: { type: "datetime" },
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
                this._super.apply(this, arguments);
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
                this._super.apply(this, arguments);
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

    QUnit.test(
        "clicking save manually after changing signature should change the unique of the image src",
        async function (assert) {
            serverData.models.partner.fields.foo = { type: "char" };
            serverData.models.partner.onchanges = { foo: () => {} };

            const rec = serverData.models.partner.records.find((rec) => rec.id === 1);
            rec.sign = "3 kb";
            rec.__last_update = "2022-08-05 08:37:00"; // 1659688620000

            // 1659692220000, 1659695820000
            const lastUpdates = ["2022-08-05 09:37:00", "2022-08-05 10:37:00"];
            let index = 0;

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: /* xml */ `
                    <form>
                        <field name="foo" />
                        <field name="sign" widget="signature" />
                    </form>`,
                mockRPC(route, { method, args }) {
                    if (route === "/web/sign/get_fonts/") {
                        return {};
                    }
                    if (method === "write") {
                        assert.step("write");
                        args[1].__last_update = lastUpdates[index];
                        args[1].sign = "4 kb";
                        index++;
                    }
                },
            });
            assert.strictEqual(
                getUnique(target.querySelector(".o_field_signature img")),
                "1659688620000"
            );

            await click(target, ".o_field_signature img", true);
            assert.containsOnce(target, ".modal canvas");

            let canvas = target.querySelector(".modal canvas");
            canvas.setAttribute("width", "2px");
            canvas.setAttribute("height", "2px");
            let ctx = canvas.getContext("2d");
            ctx.beginPath();
            ctx.strokeStyle = "blue";
            ctx.moveTo(0, 0);
            ctx.lineTo(0, 2);
            ctx.stroke();
            await triggerEvent(target, ".o_web_sign_signature", "change");
            await click(target, ".modal-footer .btn-primary");

            const MYB64 = `iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAAXNSR0IArs4c6QAAABRJREFUGFdjZGD438DAwNjACGMAACQlBAMW7JulAAAAAElFTkSuQmCC`;
            assert.strictEqual(
                target.querySelector("div[name=sign] img").dataset.src,
                `data:image/png;base64,${MYB64}`
            );

            await editInput(target, ".o_field_widget[name='foo'] input", "grrr");
            assert.strictEqual(
                target.querySelector("div[name=sign] img").dataset.src,
                `data:image/png;base64,${MYB64}`
            );

            await clickSave(target);
            assert.verifySteps(["write"]);
            assert.strictEqual(
                getUnique(target.querySelector(".o_field_signature img")),
                "1659692220000"
            );

            await click(target, ".o_field_signature img", true);
            assert.containsOnce(target, ".modal canvas");

            canvas = target.querySelector(".modal canvas");
            canvas.setAttribute("width", "2px");
            canvas.setAttribute("height", "2px");
            ctx = canvas.getContext("2d");
            ctx.beginPath();
            ctx.strokeStyle = "blue";
            ctx.moveTo(0, 0);
            ctx.lineTo(2, 0);
            ctx.stroke();
            await triggerEvent(target, ".o_web_sign_signature", "change");
            await click(target, ".modal-footer .btn-primary");

            const MYB64_2 = `iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAAXNSR0IArs4c6QAAABVJREFUGFdjZGD438DAwMDACCJAAAAWHgGCN0++VgAAAABJRU5ErkJggg==`;
            assert.notOk(MYB64 === MYB64_2);
            assert.strictEqual(
                target.querySelector("div[name=sign] img").dataset.src,
                `data:image/png;base64,${MYB64_2}`
            );
            await clickSave(target);
            assert.verifySteps(["write"]);
            assert.strictEqual(
                getUnique(target.querySelector(".o_field_signature img")),
                "1659695820000"
            );
        }
    );
});
