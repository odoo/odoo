/** @odoo-module **/
import {
    click,
    clickSave,
    editInput,
    getFixture,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { NameAndSignature } from "@web/core/signature/name_and_signature";

let serverData;
let target;

function getUnique(target) {
    const src = target.dataset.src;
    return new URL(src).searchParams.get("unique");
}

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

    QUnit.test("Set simple field in 'full_name' node option", async function (assert) {
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
        assert.verifySteps(["Pop's Chock'lit"]);
    });

    QUnit.test("Set m2o field in 'full_name' node option", async function (assert) {
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

    QUnit.test("save record with signature field modified by onchange", async function (assert) {
        const MYB64 = `iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAAXNSR0IArs4c6QAAABRJREFUGFdjZGD438DAwNjACGMAACQlBAMW7JulAAAAAElFTkSuQmCC`;

        serverData.models.partner.fields.foo = { type: "char" };
        serverData.models.partner.onchanges = {
            foo: (data) => {
                data.sign = MYB64;
            },
        };

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
        await editInput(target, "[name='foo'] input", "grrr");
        assert.strictEqual(
            target.querySelector("div[name=sign] img").dataset.src,
            `data:image/png;base64,${MYB64}`
        );

        await clickSave(target);
        assert.strictEqual(
            getUnique(target.querySelector(".o_field_signature img")),
            "1659692220000"
        );
        assert.verifySteps(["write"]);
    });
});
