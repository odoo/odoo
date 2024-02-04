odoo.define("web_domain_field.tests", function (require) {
    "use strict";

    const FormView = require("web.FormView");
    const testUtils = require("web.test_utils");
    const {createView} = testUtils;
    const {QUnit} = window;

    QUnit.module(
        "web_domain_field",
        {
            beforeEach: function () {
                this.data = {
                    "res.partner": {
                        fields: {
                            name: {
                                string: "Name",
                                type: "char",
                                searchable: true,
                            },
                            type: {
                                string: "Type",
                                type: "selection",
                                selection: [
                                    ["person", "Person"],
                                    ["company", "Company"],
                                ],
                                searchable: true,
                            },
                            parent_id: {
                                string: "Parent",
                                type: "many2one",
                                relation: "res.partner",
                            },
                            parent_domain: {
                                string: "Parent Domain",
                                type: "char",
                            },
                        },
                        records: [
                            {
                                id: 1,
                                name: "John Doe",
                                type: "person",
                                parent_id: 2,
                                parent_domain: "[]",
                            },
                            {
                                id: 2,
                                name: "ACME inc.",
                                type: "company",
                                parent_id: false,
                                parent_domain: `[["type", "=", "company"]]`,
                            },
                        ],
                        onchanges: {},
                    },
                };
            },
        },
        function () {
            QUnit.test(
                "one2many: field as domain attribute value",
                async function (assert) {
                    assert.expect(2);

                    async function testPartnerFormDomain(data, resId, expectedDomain) {
                        const form = await createView({
                            View: FormView,
                            model: "res.partner",
                            data: data,
                            arch: `
                                <form>
                                    <field name="parent_domain" invisible="1" />
                                    <field name="parent_id" domain="parent_domain" />
                                </form>
                            `,
                            mockRPC: function (route, args) {
                                if (args.method === "name_search") {
                                    assert.deepEqual(args.kwargs.args, expectedDomain);
                                }
                                return this._super.apply(this, arguments);
                            },
                            res_id: resId,
                            viewOptions: {mode: "edit"},
                        });
                        form.$el.find(".o_field_widget[name=parent_id] input").click();
                        form.destroy();
                    }

                    await testPartnerFormDomain(this.data, 1, []);
                    await testPartnerFormDomain(this.data, 2, [
                        ["type", "=", "company"],
                    ]);
                }
            );

            QUnit.test(
                "one2many: field with default behaviour",
                async function (assert) {
                    assert.expect(1);
                    const form = await createView({
                        View: FormView,
                        model: "res.partner",
                        data: this.data,
                        arch: `
                            <form>
                                <field name="parent_domain" invisible="1" />
                                <field name="parent_id" domain="[('name', '=', 'John')]" />
                            </form>
                        `,
                        mockRPC: function (route, args) {
                            if (args.method === "name_search") {
                                assert.deepEqual(args.kwargs.args, [
                                    ["name", "=", "John"],
                                ]);
                            }
                            return this._super.apply(this, arguments);
                        },
                        res_id: 1,
                        viewOptions: {mode: "edit"},
                    });
                    form.$el.find(".o_field_widget[name=parent_id] input").click();
                    form.destroy();
                }
            );
        }
    );
});
