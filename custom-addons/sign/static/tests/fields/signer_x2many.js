/** @odoo-module **/

import { getFixture, nextTick, editInput } from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

QUnit.module("Sign Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                template_request: {
                    fields: {
                        signer_ids: {
                            string: "Signers",
                            type: "one2many",
                            relation: "signer",
                        },
                        set_sign_order: {
                            string: "Set sign order",
                            type: "boolean",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            signer_ids: [1, 2],
                            set_sign_order: false,
                        },
                        {
                            id: 2,
                            signer_ids: [2],
                            set_sign_order: false,
                        },
                    ],
                },
                signer: {
                    fields: {
                        partner_id: {
                            string: "Partner",
                            type: "many2one",
                            relation: "res.partner",
                        },
                        role_id: {
                            string: "Role",
                            type: "many2one",
                            relation: "sign.item.role",
                        },
                        mail_sent_order: {
                            string: "Order",
                            type: "integer",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            partner_id: false,
                            role_id: 1,
                            mail_sent_order: 1,
                        },
                        {
                            id: 2,
                            partner_id: false,
                            role_id: 2,
                            mail_sent_order: 1,
                        },
                    ],
                },
                "sign.item.role": {
                    fields: {
                        display_name: { string: "Display name", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "Customer",
                        },
                        {
                            id: 2,
                            display_name: "Company",
                        },
                    ],
                },
                "res.partner": {
                    fields: {
                        display_name: { string: "partner", type: "char" },
                        email: { string: "email", type: "char" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "brandon",
                            email: "aed@co.co",
                        },
                        {
                            id: 2,
                            display_name: "coleen",
                            email: "abc@de.co",
                        },
                    ],
                },
            },
        };
        setupViewRegistries();
    });

    QUnit.test("basic rendering", async (assert) => {
        assert.expect(5);

        await makeView({
            type: "form",
            resModel: "template_request",
            serverData,
            arch: `
                    <form>
                        <field name="signer_ids" widget="signer_x2many"/>
                    </form>`,
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    assert.step(`name_create ${args.args[0]}`);
                }
            },
            resId: 1,
        });

        const field = target.querySelector(".o_field_signer_x2many");

        assert.containsN(field, ".d-flex.gap-2", 2, "should contain two records");
        assert.deepEqual(
            [...field.querySelectorAll(".d-flex.gap-2 label")].map((el) => el.innerText),
            ["Customer", "Company"]
        );
        assert.containsNone(
            target,
            ".o_signer_one2many_mail_sent_order",
            "mail_sent_order should not be shown."
        );

        await editInput(field.querySelector(".d-flex.gap-2"), "input", "john");
        field.querySelector(".d-flex.gap-2 input").click();
        await nextTick();
        field.querySelector(".d-flex.gap-2 .o_m2o_dropdown_option_create").click();
        await nextTick();
        assert.verifySteps(["name_create john"]);
    });

    QUnit.test("rendering with set_sign_order", async (assert) => {
        assert.expect(3);

        serverData.models.template_request.records[0].set_sign_order = true;
        await makeView({
            type: "form",
            resModel: "template_request",
            serverData,
            arch: `
                    <form>
                        <field name="signer_ids" widget="signer_x2many"/>
                    </form>`,
            resId: 1,
        });

        const field = target.querySelector(".o_field_signer_x2many");
        assert.containsN(field, ".d-flex.gap-2", 2, "should contain two records");
        assert.deepEqual(
            [...field.querySelectorAll(".d-flex.gap-2 label")].map((el) => el.innerText),
            ["Customer", "Company"]
        );
        assert.containsN(
            target,
            ".o_signer_one2many_mail_sent_order",
            2,
            "mail_sent_order should be shown in each row."
        );
    });

    QUnit.test("rendering with only one role", async (assert) => {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "template_request",
            serverData,
            arch: `
                    <form>
                        <field name="signer_ids" widget="signer_x2many"/>
                    </form>`,
            resId: 2,
        });

        const field = target.querySelector(".o_field_signer_x2many");

        assert.containsOnce(field, ".d-flex.gap-2", "should contain one record");
        assert.equal(field.querySelector(".d-flex.gap-2 label").innerText, "Company");
        assert.containsNone(
            target,
            ".o_signer_one2many_mail_sent_order",
            "mail_sent_order should not be shown."
        );
    });
});
