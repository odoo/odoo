/** @odoo-module **/

import { click } from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";
const PRODUCT_IMAGE =
    "R0lGODlhDAAMAKIFAF5LAP/zxAAAANyuAP/gaP///wAAAAAAACH5BAEAAAUALAAAAAAMAAwAAAMlWLPcGjDKFYi9lxKBOaGcF35DhWHamZUW0K4mAbiwWtuf0uxFAgA7";

let serverData;

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        serverData = {
            models: {
                partner: {
                    fields: {
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        document: { string: "Binary", type: "binary" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            timmy: [],
                            document: "coucou==\n",
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            timmy: [],
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                        },
                    ],
                },
                partner_type: {
                    fields: {
                        name: { string: "Partner Type", type: "char", searchable: true },
                        color: { string: "Color index", type: "integer", searchable: true },
                    },
                    records: [
                        { id: 12, display_name: "gold", color: 2 },
                        { id: 14, display_name: "silver", color: 5 },
                    ],
                },
            },
        };

        setupViewRegistries();
    });

    QUnit.module("ImageField");

    QUnit.test("ImageField is correctly rendered", async function (assert) {
        assert.expect(7);

        serverData.models.partner.records[0].__last_update = "2017-02-08 10:00:00";
        serverData.models.partner.records[0].document = MY_IMAGE;

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'size': [90, 90]}" />
                </form>
            `,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/read") {
                    assert.deepEqual(
                        args[1],
                        ["document", /*"__last_update",*/ "display_name"],
                        "The fields document, display_name and __last_update should be present when reading an image"
                    );
                }
                if (route === `data:image/png;base64,${MY_IMAGE}`) {
                    // FIXME: not called?
                    assert.ok(true, "should called the correct route");
                    return Promise.resolve("wow");
                }
            },
        });

        assert.hasClass(
            form.el.querySelector(".o_field_widget[name='document']"),
            "o_field_image",
            "the widget should have the correct class"
        );
        assert.containsOnce(
            form.el,
            ".o_field_widget[name='document'] > div > img",
            "the widget should contain an image"
        );
        assert.hasClass(
            form.el.querySelector(".o_field_widget[name='document'] > div > img"),
            "img-fluid",
            "the image should have the correct class"
        );
        assert.hasAttrValue(
            form.el.querySelector(".o_field_widget[name='document'] > div > img"),
            "width",
            "90",
            "the image should correctly set its attributes"
        );
        assert.strictEqual(
            form.el.querySelector(".o_field_widget[name='document'] > div > img").style.maxWidth,
            "90px",
            "the image should correctly set its attributes"
        );

        await click(form.el, ".o_form_button_edit");

        assert.strictEqual(
            form.el.querySelector("input.o_input_file").getAttribute("accept"),
            "image/*",
            'the default value for the attribute "accept" on the "image" widget must be "image/*"'
        );
    });

    QUnit.test(
        "ImageField is correctly replaced when given an incorrect value",
        async function (assert) {
            // assert.expect(7);
            assert.expect(5);

            serverData.models.partner.records[0].__last_update = "2017-02-08 10:00:00";
            serverData.models.partner.records[0].document = "incorrect_base64_value";

            // testUtils.mock.patch(basicFields.FieldBinaryImage, {
            //     // Delay the _render function: this will ensure that the error triggered
            //     // by the incorrect base64 value is dispatched before the src is replaced
            //     // (see test_utils_mock.removeSrcAttribute), since that function is called
            //     // when the element is inserted into the DOM.
            //     async _render() {
            //         const result = this._super.apply(this, arguments);
            //         await concurrency.delay(100);
            //         return result;
            //     },
            // });

            const form = await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="document" widget="image" options="{'size': [90, 90]}"/>
                    </form>
                `,
                mockRPC(route) {
                    if (route === "/web/static/img/placeholder.png") {
                        assert.step("call placeholder route"); // FIXME: not called?
                    }
                },
            });

            assert.hasClass(
                form.el.querySelector('.o_field_widget[name="document"]'),
                "o_field_image",
                "the widget should have the correct class"
            );
            assert.containsOnce(
                form,
                ".o_field_widget[name='document'] > div > img",
                "the widget should contain an image"
            );
            assert.hasClass(
                form.el.querySelector(".o_field_widget[name='document'] > div > img"),
                "img-fluid",
                "the image should have the correct class"
            );
            assert.hasAttrValue(
                form.el.querySelector(".o_field_widget[name='document'] > div > img"),
                "width",
                "90",
                "the image should correctly set its attributes"
            );
            assert.strictEqual(
                form.el.querySelector(".o_field_widget[name='document'] > div > img").style
                    .maxWidth,
                "90px",
                "the image should correctly set its attributes"
            );

            // assert.verifySteps(["call placeholder route"]);
        }
    );

    QUnit.test("ImageField: option accepted_file_extensions", async function (assert) {
        assert.expect(1);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'accepted_file_extensions': '.png,.jpeg'}" />
                </form>
            `,
        });
        // The view must be in edit mode
        await click(form.el.querySelector(".o_form_button_edit"));
        assert.strictEqual(
            form.el.querySelector("input.o_input_file").getAttribute("accept"),
            ".png,.jpeg",
            "the input should have the correct ``accept`` attribute"
        );
    });

    QUnit.test("ImageField in subviews is loaded correctly", async function (assert) {
        assert.expect(2);
        //assert.expect(6);

        serverData.models.partner.records[0].__last_update = "2017-02-08 10:00:00";
        serverData.models.partner.records[0].document = MY_IMAGE;
        serverData.models.partner_type.fields.image = { name: "image", type: "binary" };
        serverData.models.partner_type.records[0].image = PRODUCT_IMAGE;
        serverData.models.partner.records[0].timmy = [12];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'size': [90, 90]}" />
                    <field name="timmy" widget="many2many" mode="kanban">
                        <!-- use kanban view as the tree will trigger edit mode and thus won't display the field -->
                        <kanban>
                            <field name="display_name" />
                            <templates>
                                <t t-name="kanban-box">
                                    <div class="oe_kanban_global_click">
                                        <span>
                                            <t t-esc="record.display_name.value" />
                                        </span>
                                    </div>
                                </t>
                            </templates>
                        </kanban>
                        <form>
                            <field name="image" widget="image" />
                        </form>
                    </field>
                </form>
            `,
            /*
            mockRPC(route) {
                if (route === `data:image/png;base64,${MY_IMAGE}`) {
                    assert.step("The view's image should have been fetched");
                    return "wow";
                }
                if (route === `data:image/gif;base64,${PRODUCT_IMAGE}`) {
                    assert.step("The dialog's image should have been fetched");
                    return;
                }
            },*/
        });
        //assert.verifySteps(["The view's image should have been fetched"]);

        assert.containsOnce(
            form,
            ".o_kanban_record.oe_kanban_global_click",
            "There should be one record in the many2many"
        );

        // Actual flow: click on an element of the m2m to get its form view
        await click(form.el, ".oe_kanban_global_click");
        assert.strictEqual($(".modal").length, 1, "The modal should have opened");
        //assert.verifySteps(["The dialog's image should have been fetched"]);
    });

    QUnit.skipWOWL("ImageField in x2many list is loaded correctly", async function (assert) {
        assert.expect(2);

        serverData.models.partner_type.fields.image = { name: "image", type: "binary" };
        serverData.models.partner_type.records[0].image = PRODUCT_IMAGE;
        serverData.models.partner.records[0].timmy = [12];

        const form = await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many">
                        <tree>
                            <field name="image" widget="image" />
                        </tree>
                    </field>
                </form>
            `,
            mockRPC(route) {
                if (route === `data:image/gif;base64,${PRODUCT_IMAGE}`) {
                    assert.ok(true, "The list's image should have been fetched");
                    return;
                }
            },
        });

        assert.containsOnce(form, "tr.o_data_row", "There should be one record in the many2many");
    });

    QUnit.skipWOWL("ImageField with required attribute", async function (assert) {
        assert.expect(2);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" required="1" />
                </form>
            `,
            mockRPC(route, { method }) {
                if (method === "create") {
                    throw new Error("Should not do a create RPC with unset required image field");
                }
            },
        });

        await click(form.el, ".o_form_button_save");

        assert.hasClass(
            form.el.querySelector(".o_form_view"),
            "o_form_editable",
            "form view should still be editable"
        );
        assert.hasClass(
            form.el.querySelector(".o_field_widget"),
            "o_field_invalid",
            "image field should be displayed as invalid"
        );
    });
});
