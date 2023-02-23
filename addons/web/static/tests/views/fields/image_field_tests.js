/** @odoo-module **/

import {
    click,
    getFixture,
    nextTick,
    triggerEvent,
    clickSave,
    editInput,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { pagerNext } from "@web/../tests/search/helpers";

const MY_IMAGE =
    "iVBORw0KGgoAAAANSUhEUgAAAAUAAAAFCAYAAACNbyblAAAAHElEQVQI12P4//8/w38GIAXDIBKE0DHxgljNBAAO9TXL0Y4OHwAAAABJRU5ErkJggg==";
const PRODUCT_IMAGE =
    "R0lGODlhDAAMAKIFAF5LAP/zxAAAANyuAP/gaP///wAAAAAAACH5BAEAAAUALAAAAAAMAAwAAAMlWLPcGjDKFYi9lxKBOaGcF35DhWHamZUW0K4mAbiwWtuf0uxFAgA7";

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
                        display_name: { string: "Displayed name", type: "char", searchable: true },
                        timmy: {
                            string: "pokemon",
                            type: "many2many",
                            relation: "partner_type",
                            searchable: true,
                        },
                        foo: { type: "char" },
                        document: { string: "Binary", type: "binary" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            timmy: [],
                            document: "coucou==",
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
        assert.expect(10);

        serverData.models.partner.records[0].write_date = "2017-02-08 10:00:00";
        serverData.models.partner.records[0].document = MY_IMAGE;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'size': [90, 90]}" />
                </form>`,
            mockRPC(route, { args }) {
                if (route === "/web/dataset/call_kw/partner/read") {
                    assert.deepEqual(
                        args[1],
                        ["write_date", "document", "display_name"],
                        "The fields document, display_name and write_date should be present when reading an image"
                    );
                }
            },
        });

        assert.hasClass(
            target.querySelector(".o_field_widget[name='document']"),
            "o_field_image",
            "the widget should have the correct class"
        );
        assert.containsOnce(
            target,
            ".o_field_widget[name='document'] img",
            "the widget should contain an image"
        );
        assert.strictEqual(
            target.querySelector('div[name="document"] img').dataset.src,
            `data:image/png;base64,${MY_IMAGE}`,
            "the image should have the correct src"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget[name='document'] img"),
            "img-fluid",
            "the image should have the correct class"
        );
        assert.hasAttrValue(
            target.querySelector(".o_field_widget[name='document'] img"),
            "width",
            "90",
            "the image should correctly set its attributes"
        );
        assert.strictEqual(
            target.querySelector(".o_field_widget[name='document'] img").style.maxWidth,
            "90px",
            "the image should correctly set its attributes"
        );

        assert.containsOnce(
            target,
            ".o_field_image .o_select_file_button",
            "the image can be edited"
        );
        assert.containsOnce(
            target,
            ".o_field_image .o_clear_file_button",
            "the image can be deleted"
        );
        assert.strictEqual(
            target.querySelector("input.o_input_file").getAttribute("accept"),
            "image/*",
            'the default value for the attribute "accept" on the "image" widget must be "image/*"'
        );
    });

    QUnit.test(
        "ImageField is correctly replaced when given an incorrect value",
        async function (assert) {
            serverData.models.partner.records[0].document = "incorrect_base64_value";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                    <form>
                        <field name="document" widget="image" options="{'size': [90, 90]}"/>
                    </form>`,
            });

            assert.strictEqual(
                target.querySelector('div[name="document"] img').dataset.src,
                "data:image/png;base64,incorrect_base64_value",
                "the image has the invalid src by default"
            );

            // As GET requests can't occur in tests, we must generate an error
            // on the img element to check whether the data-src is replaced with
            // a placeholder, here knowing that the GET request would fail
            await triggerEvent(target, 'div[name="document"] img', "error");

            assert.hasClass(
                target.querySelector('.o_field_widget[name="document"]'),
                "o_field_image",
                "the widget should have the correct class"
            );
            assert.containsOnce(
                target,
                ".o_field_widget[name='document'] img",
                "the widget should contain an image"
            );
            assert.strictEqual(
                target.querySelector('div[name="document"] img').dataset.src,
                "/web/static/img/placeholder.png",
                "the image should have the correct src"
            );
            assert.hasClass(
                target.querySelector(".o_field_widget[name='document'] img"),
                "img-fluid",
                "the image should have the correct class"
            );
            assert.hasAttrValue(
                target.querySelector(".o_field_widget[name='document'] img"),
                "width",
                "90",
                "the image should correctly set its attributes"
            );
            assert.strictEqual(
                target.querySelector(".o_field_widget[name='document'] img").style.maxWidth,
                "90px",
                "the image should correctly set its attributes"
            );

            assert.containsOnce(
                target,
                ".o_field_image .o_select_file_button",
                "the image can be edited"
            );
            assert.containsNone(
                target,
                ".o_field_image .o_clear_file_button",
                "the image cannot be deleted as it has not been uploaded"
            );
        }
    );

    QUnit.test("ImageField preview is updated when an image is uploaded", async function (assert) {
        const imageData = Uint8Array.from([...atob(MY_IMAGE)].map((c) => c.charCodeAt(0)));
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `<form>
                <field name="document" widget="image" options="{'size': [90, 90]}"/>
            </form>`,
        });

        assert.strictEqual(
            target.querySelector('div[name="document"] img').dataset.src,
            "data:image/png;base64,coucou==",
            "the image should have the initial src"
        );
        // Whitebox: replace the event target before the event is handled by the field so that we can modify
        // the files that it will take into account. This relies on the fact that it reads the files from
        // event.target and not from a direct reference to the input element.
        const fileInput = target.querySelector("input[type=file]");
        const fakeInput = {
            files: [new File([imageData], "fake_file.png", { type: "png" })],
        };
        fileInput.addEventListener(
            "change",
            (ev) => {
                Object.defineProperty(ev, "target", { value: fakeInput });
            },
            { capture: true }
        );

        fileInput.dispatchEvent(new Event("change"));
        // It can take some time to encode the data as a base64 url
        await new Promise((resolve) => setTimeout(resolve, 50));
        // Wait for a render
        await nextTick();
        assert.strictEqual(
            target.querySelector("div[name=document] img").dataset.src,
            `data:image/png;base64,${MY_IMAGE}`,
            "the image should have the new src"
        );
    });

    QUnit.test(
        "clicking save manually after uploading new image should change the unique of the image src",
        async function (assert) {
            serverData.models.partner.onchanges = { foo: () => {} };

            const rec = serverData.models.partner.records.find((rec) => rec.id === 1);
            rec.document = "3 kb";
            rec.write_date = "2022-08-05 08:37:00"; // 1659688620000

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: /* xml */ `
                    <form>
                        <field name="foo"/>
                        <field name="document" widget="image" />
                    </form>`,
                mockRPC(_route, { method, args }) {
                    if (method === "write") {
                        args[1].write_date = "2022-08-05 09:37:00"; // 1659692220000
                        args[1].document = "4 kb";
                    }
                },
            });
            assert.strictEqual(
                getUnique(target.querySelector(".o_field_image img")),
                "1659688620000"
            );

            await editInput(
                target,
                "input[type=file]",
                new File(
                    [Uint8Array.from([...atob(MY_IMAGE)].map((c) => c.charCodeAt(0)))],
                    "fake_file.png",
                    { type: "png" }
                )
            );
            assert.strictEqual(
                target.querySelector("div[name=document] img").dataset.src,
                `data:image/png;base64,${MY_IMAGE}`
            );

            await editInput(target, ".o_field_widget[name='foo'] input", "grrr");
            assert.strictEqual(
                target.querySelector("div[name=document] img").dataset.src,
                `data:image/png;base64,${MY_IMAGE}`
            );

            await clickSave(target);
            assert.strictEqual(
                getUnique(target.querySelector(".o_field_image img")),
                "1659692220000"
            );
        }
    );

    QUnit.test("ImageField: option accepted_file_extensions", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'accepted_file_extensions': '.png,.jpeg'}" />
                </form>`,
        });
        // The view must be in edit mode
        assert.strictEqual(
            target.querySelector("input.o_input_file").getAttribute("accept"),
            ".png,.jpeg",
            "the input should have the correct ``accept`` attribute"
        );
    });

    QUnit.test("ImageField: set 0 width/height in the size option", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'size': [0, 0]}" />
                    <field name="document" widget="image" options="{'size': [0, 50]}" />
                    <field name="document" widget="image" options="{'size': [50, 0]}" />
                </form>`,
        });
        const imgs = target.querySelectorAll(".o_field_widget img");
        assert.deepEqual(
            [imgs[0].attributes.width, imgs[0].attributes.height],
            [undefined, undefined],
            "if both size are set to 0, both attributes are undefined"
        );
        assert.deepEqual(
            [imgs[1].attributes.width, imgs[1].attributes.height.value],
            [undefined, "50"],
            "if only the width is set to 0, the width attribute is not set on the img"
        );
        assert.deepEqual(
            [imgs[2].attributes.width.value, imgs[2].attributes.height],
            ["50", undefined],
            "if only the height is set to 0, the height attribute is not set on the img"
        );
    });

    QUnit.test("ImageField: zoom and zoom_delay options (readonly)", async (assert) => {
        serverData.models.partner.records[0].document = MY_IMAGE;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'zoom': true, 'zoom_delay': 600}" readonly="1" />
                </form>`,
        });
        // data-tooltip attribute is used by the tooltip service
        assert.strictEqual(
            JSON.parse(target.querySelector(".o_field_image img").dataset["tooltipInfo"]).url,
            `data:image/png;base64,${MY_IMAGE}`,
            "shows a tooltip on hover"
        );
        assert.strictEqual(
            target.querySelector(".o_field_image img").dataset["tooltipDelay"],
            "600",
            "tooltip has the right delay"
        );
    });

    QUnit.test("ImageField: zoom and zoom_delay options (edit)", async function (assert) {
        serverData.models.partner.records[0].document = MY_IMAGE;

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'zoom': true, 'zoom_delay': 600}" />
                </form>`,
        });

        assert.ok(
            !target.querySelector(".o_field_image img").dataset["tooltipInfo"],
            "the tooltip is not present in edition"
        );
    });

    QUnit.test(
        "ImageField displays the right images with zoom and preview_image options (readonly)",
        async function (assert) {
            serverData.models.partner.records[0].document = "3 kb";
            serverData.models.partner.records[0].write_date = "2022-08-05 08:37:00";

            await makeView({
                type: "form",
                resModel: "partner",
                resId: 1,
                serverData,
                arch: `
                <form>
                    <field name="document" widget="image" options="{'zoom': true, 'preview_image': 'document_preview', 'zoom_delay': 600}" readonly="1" />
                </form>`,
            });

            assert.ok(
                JSON.parse(
                    target.querySelector(".o_field_image img").dataset["tooltipInfo"]
                ).url.endsWith("/web/image?model=partner&id=1&field=document&unique=1659688620000"),
                "tooltip show the full image from the field value"
            );
            assert.strictEqual(
                target.querySelector(".o_field_image img").dataset["tooltipDelay"],
                "600",
                "tooltip has the right delay"
            );
            assert.ok(
                target
                    .querySelector(".o_field_image img")
                    .dataset.src.endsWith(
                        "/web/image?model=partner&id=1&field=document_preview&unique=1659688620000"
                    ),
                "image src is the preview image given in option"
            );
        }
    );

    QUnit.test("ImageField in subviews is loaded correctly", async function (assert) {
        serverData.models.partner.records[0].write_date = "2017-02-08 10:00:00";
        serverData.models.partner.records[0].document = MY_IMAGE;
        serverData.models.partner_type.fields.image = { name: "image", type: "binary" };
        serverData.models.partner_type.records[0].image = PRODUCT_IMAGE;
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" options="{'size': [90, 90]}" />
                    <field name="timmy" widget="many2many" mode="kanban">
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
                </form>`,
        });

        assert.containsOnce(target, `img[data-src="data:image/png;base64,${MY_IMAGE}"]`);
        assert.containsOnce(target, ".o_kanban_record .oe_kanban_global_click");

        // Actual flow: click on an element of the m2m to get its form view
        await click(target, ".oe_kanban_global_click");
        assert.containsOnce(target, ".modal", "The modal should have opened");

        assert.containsOnce(target, `img[data-src="data:image/gif;base64,${PRODUCT_IMAGE}"]`);
    });

    QUnit.test("ImageField in x2many list is loaded correctly", async function (assert) {
        serverData.models.partner_type.fields.image = { name: "image", type: "binary" };
        serverData.models.partner_type.records[0].image = PRODUCT_IMAGE;
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
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
                </form>`,
        });

        assert.containsOnce(target, "tr.o_data_row", "There should be one record in the many2many");
        assert.ok(
            document.querySelector(`img[data-src="data:image/gif;base64,${PRODUCT_IMAGE}"]`),
            "The list's image is in the DOM"
        );
    });

    QUnit.test("ImageField with required attribute", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" required="1" />
                </form>`,
            mockRPC(route, { method }) {
                if (method === "create") {
                    throw new Error("Should not do a create RPC with unset required image field");
                }
            },
        });

        await clickSave(target);

        assert.containsOnce(
            target.querySelector(".o_form_view"),
            ".o_form_editable",
            "form view should still be editable"
        );
        assert.hasClass(
            target.querySelector(".o_field_widget"),
            "o_field_invalid",
            "image field should be displayed as invalid"
        );
    });

    QUnit.test("unique in url doesn't change on onchange", async (assert) => {
        serverData.models.partner.onchanges = {
            foo: () => {},
        };

        const rec = serverData.models.partner.records.find((rec) => rec.id === 1);
        rec.document = "3 kb";
        rec.write_date = "2022-08-05 08:37:00";

        await makeView({
            resId: 1,
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo" />
                    <field name="document" widget="image" required="1" />
                </form>`,
            mockRPC(route, { method, args }) {
                assert.step(method);
                if (method === "onchange") {
                    return {
                        value: {
                            write_date: "", // actual return of the server
                        },
                    };
                }
                if (method === "write") {
                    args[1].write_date = "2022-08-05 09:37:00";
                }
            },
        });

        assert.verifySteps(["get_views", "read"]);
        assert.strictEqual(getUnique(target.querySelector(".o_field_image img")), "1659688620000");

        assert.verifySteps([]);
        // same unique as before
        assert.strictEqual(getUnique(target.querySelector(".o_field_image img")), "1659688620000");

        await editInput(target, ".o_field_widget[name='foo'] input", "grrr");
        assert.verifySteps(["onchange"]);
        // also same unique
        assert.strictEqual(getUnique(target.querySelector(".o_field_image img")), "1659688620000");

        await clickSave(target);
        assert.verifySteps(["write", "read"]);

        assert.strictEqual(getUnique(target.querySelector(".o_field_image img")), "1659688620000");
    });

    QUnit.test("unique in url change on record change", async (assert) => {
        const rec = serverData.models.partner.records.find((rec) => rec.id === 1);
        rec.document = "3 kb";
        rec.write_date = "2022-08-05 08:37:00";

        const rec2 = serverData.models.partner.records.find((rec) => rec.id === 2);
        rec2.document = "3 kb";
        rec2.write_date = "2022-08-05 09:37:00";

        await makeView({
            resIds: [1, 2],
            resId: 1,
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="document" widget="image" required="1" />
                </form>`,
        });

        function getUnique(target) {
            const src = target.dataset.src;
            return new URL(src).searchParams.get("unique");
        }

        assert.strictEqual(getUnique(target.querySelector(".o_field_image img")), "1659688620000");
        await pagerNext(target);
        assert.strictEqual(getUnique(target.querySelector(".o_field_image img")), "1659692220000");
    });
});
