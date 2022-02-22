/** @odoo-module **/

import { browser } from "@web/core/browser/browser";
import { click, getFixture, patchWithCleanup } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        foo: { string: "Foo", type: "char", default: "My little Foo Value" },
                        bar: { string: "Bar", type: "boolean", default: true },
                        int_field: { string: "int_field", type: "integer", sortable: true },
                        qux: { string: "Qux", type: "float", digits: [16, 1] },
                        p: {
                            string: "one2many field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "trululu",
                        },
                        turtles: {
                            string: "one2many turtle field",
                            type: "one2many",
                            relation: "turtle",
                            relation_field: "turtle_trululu",
                        },
                        trululu: { string: "Trululu", type: "many2one", relation: "partner" },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                        product_id: { string: "Product", type: "many2one", relation: "product" },
                        color: {
                            type: "selection",
                            selection: [
                                ["red", "Red"],
                                ["black", "Black"],
                            ],
                            default: "red",
                            string: "Color",
                        },
                        date: { string: "Some Date", type: "date" },
                        datetime: { string: "Datetime Field", type: "datetime" },
                        user_id: { string: "User", type: "many2one", relation: "user" },
                        reference: {
                            string: "Reference Field",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner_type", "Partner Type"],
                                ["partner", "Partner"],
                            ],
                        },
                        model_id: { string: "Model", type: "many2one", relation: "ir.model" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            bar: true,
                            foo: "yop",
                            int_field: 10,
                            qux: 0.44,
                            p: [],
                            turtles: [2],
                            timmy: [],
                            trululu: 4,
                            user_id: 17,
                            reference: "product,37",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            bar: true,
                            foo: "blip",
                            int_field: 9,
                            qux: 13,
                            p: [],
                            timmy: [],
                            trululu: 1,
                            product_id: 37,
                            date: "2017-01-25",
                            datetime: "2016-12-12 10:55:05",
                            user_id: 17,
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                            bar: false,
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
                            id: 37,
                            display_name: "xphone",
                        },
                        {
                            id: 41,
                            display_name: "xpad",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char" },
                        color: { string: "Color index", type: "integer" },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
                turtle: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char" },
                        turtle_foo: { string: "Foo", type: "char" },
                        turtle_bar: { string: "Bar", type: "boolean", default: true },
                        turtle_int: { string: "int", type: "integer", sortable: true },
                        turtle_description: { string: "Description", type: "text" },
                        turtle_trululu: {
                            string: "Trululu",
                            type: "many2one",
                            relation: "partner",
                        },
                        turtle_ref: {
                            string: "Reference",
                            type: "reference",
                            selection: [
                                ["product", "Product"],
                                ["partner", "Partner"],
                            ],
                        },
                        product_id: {
                            string: "Product",
                            type: "many2one",
                            relation: "product",
                            required: true,
                        },
                        partner_ids: { string: "Partner", type: "many2many", relation: "partner" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "leonardo",
                            turtle_bar: true,
                            turtle_foo: "yop",
                            partner_ids: [],
                        },
                        {
                            id: 2,
                            display_name: "donatello",
                            turtle_bar: true,
                            turtle_foo: "blip",
                            turtle_int: 9,
                            partner_ids: [2, 4],
                        },
                        {
                            id: 3,
                            display_name: "raphael",
                            product_id: 37,
                            turtle_bar: false,
                            turtle_foo: "kawa",
                            turtle_int: 21,
                            partner_ids: [],
                            turtle_ref: "product,37",
                        },
                    ],
                    onchanges: {},
                },
                user: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        partner_ids: {
                            string: "one2many partners field",
                            type: "one2many",
                            relation: "partner",
                            relation_field: "user_id",
                        },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Aline",
                            partner_ids: [1, 2],
                        },
                        {
                            id: 19,
                            name: "Christine",
                        },
                    ],
                },
                "ir.model": {
                    fields: {
                        model: { string: "Model", type: "char" },
                    },
                    records: [
                        {
                            id: 17,
                            name: "Partner",
                            model: "partner",
                        },
                        {
                            id: 20,
                            name: "Product",
                            model: "product",
                        },
                        {
                            id: 21,
                            name: "Partner Type",
                            model: "partner_type",
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("StatusBarField");

    QUnit.skipWOWL("static statusbar widget on many2one field", async function (assert) {
        assert.expect(5);

        serverData.models.partner.fields.trululu.domain = "[('bar', '=', True)]";
        serverData.models.partner.records[1].bar = false;

        var count = 0;
        var nb_fields_fetched;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                '<header><field name="trululu" widget="statusbar"/></header>' +
                // the following field seem useless, but its presence was the
                // cause of a crash when evaluating the field domain.
                '<field name="timmy" invisible="1"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "search_read") {
                    count++;
                    nb_fields_fetched = args.kwargs.fields.length;
                }
                return this._super.apply(this, arguments);
            },
            resId: 1,
            config: { device: { isMobile: false } },
        });

        assert.strictEqual(
            count,
            1,
            "once search_read should have been done to fetch the relational values"
        );
        assert.strictEqual(nb_fields_fetched, 1, "search_read should only fetch field id");
        assert.containsN(form, ".o_statusbar_status button:not(.dropdown-toggle)", 2);
        assert.containsN(form, ".o_statusbar_status button:disabled", 2);
        assert.hasClass(form.$('.o_statusbar_status button[data-value="4"]'), "btn-primary");
        form.destroy();
    });

    QUnit.skipWOWL(
        "static statusbar widget on many2one field with domain",
        async function (assert) {
            assert.expect(1);

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch:
                    '<form string="Partners">' +
                    '<header><field name="trululu" domain="[(\'user_id\',\'=\',uid)]" widget="statusbar"/></header>' +
                    "</form>",
                mockRPC: function (route, args) {
                    if (args.method === "search_read") {
                        assert.deepEqual(
                            args.kwargs.domain,
                            ["|", ["id", "=", 4], ["user_id", "=", 17]],
                            "search_read should sent the correct domain"
                        );
                    }
                    return this._super.apply(this, arguments);
                },
                resId: 1,
                session: { user_context: { uid: 17 } },
            });

            form.destroy();
        }
    );

    QUnit.test("clickable statusbar widget on many2one field", async function (assert) {
        assert.expect(5);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="trululu" widget="statusbar" options="{'clickable': 1}" />
                    </header>
                </form>
            `,
            // config: { device: { isMobile: false } },
        });

        assert.hasClass(
            target.querySelector(".o_statusbar_status button[data-value='4']"),
            "btn-primary"
        );
        assert.hasClass(
            target.querySelector(".o_statusbar_status button[data-value='4']"),
            "disabled"
        );

        const clickableButtons = target.querySelectorAll(
            ".o_statusbar_status button.btn-secondary:not(.dropdown-toggle):not(:disabled)"
        );
        assert.strictEqual(clickableButtons.length, 2);

        await click(clickableButtons[clickableButtons.length - 1]); // (last is visually the first here (css))

        assert.hasClass(
            target.querySelector(".o_statusbar_status button[data-value='1']"),
            "btn-primary"
        );
        assert.hasClass(
            target.querySelector(".o_statusbar_status button[data-value='1']"),
            "disabled"
        );
    });

    QUnit.test("statusbar with no status", async function (assert) {
        assert.expect(2);

        serverData.models.product.records = [];
        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="product_id" widget="statusbar" />
                    </header>
                </form>
            `,
            // config: { device: { isMobile: false } },
        });

        assert.doesNotHaveClass(target.querySelector(".o_statusbar_status"), "o_field_empty");
        assert.strictEqual(
            target.querySelector(".o_statusbar_status").children.length,
            0,
            "statusbar widget should be empty"
        );
    });

    QUnit.skipWOWL("statusbar with required modifier", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form string="Partners">
                    <header><field name="product_id" widget="statusbar" required="1"/></header>
                </form>`,
            config: { device: { isMobile: false } },
        });
        testUtils.mock.intercept(
            form,
            "call_service",
            function (ev) {
                assert.strictEqual(
                    ev.data.service,
                    "notification",
                    "should display an 'invalid fields' notification"
                );
            },
            true
        );

        testUtils.form.clickSave(form);

        assert.containsOnce(form, ".o_form_editable", "view should still be in edit");

        form.destroy();
    });

    QUnit.test("statusbar with no value in readonly", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <header>
                        <field name="product_id" widget="statusbar" />
                    </header>
                </form>
            `,
            // config: { device: { isMobile: false } },
        });

        assert.doesNotHaveClass(target.querySelector(".o_statusbar_status"), "o_field_empty");
        assert.containsN(target, ".o_statusbar_status button:visible", 2);
    });

    QUnit.skipWOWL("statusbar with domain but no value (create mode)", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.trululu.domain = "[('bar', '=', True)]";

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                '<header><field name="trululu" widget="statusbar"/></header>' +
                "</form>",
            config: { device: { isMobile: false } },
        });

        assert.containsN(form, ".o_statusbar_status button:disabled", 2);
        form.destroy();
    });

    QUnit.skipWOWL(
        "clickable statusbar should change m2o fetching domain in edit mode",
        async function (assert) {
            assert.expect(2);

            serverData.models.partner.fields.trululu.domain = "[('bar', '=', True)]";

            const form = await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch:
                    '<form string="Partners">' +
                    '<header><field name="trululu" widget="statusbar" options=\'{"clickable": "1"}\'/></header>' +
                    "</form>",
                resId: 1,
                config: { device: { isMobile: false } },
            });

            await testUtils.form.clickEdit(form);
            assert.containsN(form, ".o_statusbar_status button:not(.dropdown-toggle)", 3);
            await testUtils.dom.click(
                form.$(".o_statusbar_status button:not(.dropdown-toggle)").last()
            );
            assert.containsN(form, ".o_statusbar_status button:not(.dropdown-toggle)", 2);

            form.destroy();
        }
    );

    QUnit.test(
        "statusbar fold_field option and statusbar_visible attribute",
        async function (assert) {
            assert.expect(2);

            patchWithCleanup(browser, {
                setTimeout: (fn) => fn(),
            });

            serverData.models.partner.records[0].bar = false;

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <header>
                            <field name="trululu" widget="statusbar" options="{'fold_field': 'bar'}" />
                            <field name="color" widget="statusbar" statusbar_visible="red" />
                        </header>
                    </form>
                `,
                // config: { device: { isMobile: false } },
            });

            await click(target, ".o_form_button_edit");
            await click(target, ".o_statusbar_status .dropdown-toggle");

            const status = target.querySelectorAll(".o_statusbar_status");
            assert.containsOnce(status[0], ".dropdown-item.disabled");
            assert.containsOnce(status[status.length - 1], "button.disabled");
        }
    );

    QUnit.skipWOWL("statusbar with dynamic domain", async function (assert) {
        assert.expect(5);

        serverData.models.partner.fields.trululu.domain = "[('int_field', '>', qux)]";
        serverData.models.partner.records[2].int_field = 0;

        var rpcCount = 0;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch:
                '<form string="Partners">' +
                '<header><field name="trululu" widget="statusbar"/></header>' +
                '<field name="qux"/>' +
                '<field name="foo"/>' +
                "</form>",
            mockRPC: function (route, args) {
                if (args.method === "search_read") {
                    rpcCount++;
                }
                return this._super.apply(this, arguments);
            },
            resId: 1,
            config: { device: { isMobile: false } },
        });

        await testUtils.form.clickEdit(form);

        assert.containsN(form, ".o_statusbar_status button.disabled", 3);
        assert.strictEqual(rpcCount, 1, "should have done 1 search_read rpc");
        await testUtils.fields.editInput(form.$("input[name=qux]"), 9.5);
        assert.containsN(form, ".o_statusbar_status button.disabled", 2);
        assert.strictEqual(rpcCount, 2, "should have done 1 more search_read rpc");
        await testUtils.fields.editInput(form.$("input[name=qux]"), "hey");
        assert.strictEqual(rpcCount, 2, "should not have done 1 more search_read rpc");

        form.destroy();
    });

    // TODO: Once the code base is converted with wowl, replace webclient by formview.
    QUnit.skipWOWL(
        'statusbar edited by the smart action "Move to stage..."',
        async function (assert) {
            assert.expect(3);

            const legacyEnv = makeTestEnvironment({ bus: core.bus });
            const serviceRegistry = registry.category("services");
            serviceRegistry.add("legacy_command", makeLegacyCommandService(legacyEnv));

            const views = {
                "partner,false,form":
                    "<form>" +
                    '<header><field name="trululu" widget="statusbar" options=\'{"clickable": "1"}\'/></header>' +
                    "</form>",
                "partner,false,search": "<search></search>",
            };
            const serverData = { models: this.data, views };
            const webClient = await createWebClient({ serverData });
            await doAction(webClient, {
                res_id: 1,
                type: "ir.actions.act_window",
                target: "current",
                res_model: "partner",
                view_mode: "form",
                views: [[false, "form"]],
            });
            assert.containsOnce(webClient, ".o_field_widget");

            triggerHotkey("control+k");
            await nextTick();
            const movestage = webClient.el.querySelectorAll(".o_command");
            const idx = [...movestage]
                .map((el) => el.textContent)
                .indexOf("Move to Trululu...ALT + SHIFT + X");
            assert.ok(idx >= 0);

            await click(movestage[idx]);
            await nextTick();
            assert.deepEqual(
                [...webClient.el.querySelectorAll(".o_command")].map((el) => el.textContent),
                ["first record", "second record", "aaa"]
            );
            await click(webClient.el, "#o_command_2");
        }
    );
});
