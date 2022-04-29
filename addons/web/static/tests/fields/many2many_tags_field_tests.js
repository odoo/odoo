/** @odoo-module **/

import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { Many2ManyTagsField } from "@web/fields/many2many_tags_field";
import {
    click,
    clickDropdown,
    clickEdit,
    clickOpenedDropdownItem,
    clickSave,
    editInput,
    getFixture,
    getNodesTextContent,
    nextTick,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
} from "../helpers/utils";
import { makeView, setupViewRegistries } from "../views/helpers";

let serverData;
let target;

// WOWL remove after adapting tests
let createView, FormView, testUtils;

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

    QUnit.module("Many2ManyTagsField");

    QUnit.test("fieldmany2many tags with and without color", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.partner_ids = {
            string: "Partner",
            type: "many2many",
            relation: "partner",
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                    <field name="partner_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
            mockRPC: (route, { args, method, model }) => {
                if (method === "read" && model === "partner_type") {
                    assert.deepEqual(
                        args,
                        [[12], ["display_name"]],
                        "should not read any color field"
                    );
                } else if (method === "read" && model === "partner") {
                    assert.deepEqual(
                        args,
                        [[1], ["display_name", "color"]],
                        "should read color field"
                    );
                }
            },
        });

        await selectDropdownItem(target, "partner_ids", "first record");

        await clickDropdown(target, "timmy");
        const autocomplete = target.querySelector("[name='timmy'] .o-autocomplete.dropdown");
        assert.strictEqual(
            autocomplete.querySelectorAll("li").length,
            3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')"
        );
        await clickOpenedDropdownItem(target, "timmy", "gold");
        assert.strictEqual(
            getNodesTextContent(
                target.querySelectorAll(`.o_field_many2many_tags[name="timmy"] .badge`)
            ),
            "gold"
        );
    });

    QUnit.test("fieldmany2many tags with color: rendering and edition", async function (assert) {
        assert.expect(28);

        serverData.models.partner.records[0].timmy = [12, 14];
        serverData.models.partner_type.records.push({ id: 13, display_name: "red", color: 8 });
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'color_field': 'color', 'no_create_edit': True }"/>
                </form>`,
            resId: 1,
            mockRPC: (route, { args, method, model }) => {
                if (route === "/web/dataset/call_kw/partner/write") {
                    var commands = args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(
                        commands[0][0],
                        6,
                        "generated command should be REPLACE WITH"
                    );
                    assert.deepEqual(commands[0][2], [12, 13], "new value should be [12, 13]");
                }
                if (method === "read" && model === "partner_type") {
                    assert.deepEqual(
                        args[1],
                        ["display_name", "color"],
                        "should read the color field"
                    );
                }
            },
        });
        assert.containsN(target, ".o_field_many2many_tags .badge", 2, "should contain 2 tags");
        assert.strictEqual(
            target.querySelector(".badge .o_tag_badge_text").textContent,
            "gold",
            "should have fetched and rendered gold partner tag"
        );
        assert.strictEqual(
            target.querySelectorAll(".badge .o_tag_badge_text")[1].textContent,
            "silver",
            "should have fetched and rendered silver partner tag"
        );
        assert.hasClass(
            target.querySelector(".badge"),
            "o_tag_color_2",
            "should have correctly set the color"
        );

        await clickEdit(target);

        assert.containsN(
            target,
            ".o_field_many2many_tags .badge",
            2,
            "should still contain 2 tags in edit mode"
        );
        assert.ok(
            target.querySelector(".o_tag_color_2 .o_tag_badge_text").textContent === "gold",
            'first tag should still contain "gold" and be color 2 in edit mode'
        );
        assert.containsN(
            target,
            ".o_field_many2many_tags .o_delete",
            2,
            "tags should contain a delete button"
        );

        // add an other existing tag
        await click(target.querySelector("div[name='timmy'] .o-autocomplete.dropdown input"));

        const autocompleteDropdown = target.querySelector(".o-autocomplete--dropdown-menu");

        assert.strictEqual(
            autocompleteDropdown.querySelectorAll("li").length,
            2,
            "autocomplete dropdown should have 2 entry"
        );

        assert.strictEqual(
            autocompleteDropdown.querySelector("li a").textContent,
            "red",
            "autocomplete dropdown should contain 'red'"
        );

        await click(autocompleteDropdown.querySelector("li a"));
        assert.containsN(target, ".o_field_many2many_tags .badge", 3, "should contain 3 tags");
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2many_tags .badge .o_tag_badge_text")[2]
                .textContent,
            "red",
            "should contain newly added tag 'red'"
        );
        assert.hasClass(
            target.querySelectorAll(".badge")[2],
            "o_tag_color_8",
            "should have fetched the color of added tag"
        );

        // remove tag silver
        await click(target.querySelectorAll(".o_field_many2many_tags .o_delete")[1]);
        assert.containsN(target, ".o_field_many2many_tags .badge", 2, "should contain 2 tags");
        const textContent = getNodesTextContent(
            target.querySelectorAll(".o_field_many2many_tags  .dropdown-toggle .badge")
        );
        assert.strictEqual(
            textContent.includes("silver"),
            false,
            `should not contain tag 'silver' anymore but found: ${textContent}`
        );
        // save the record (should do the write RPC with the correct commands)
        await click(target.querySelector(".o_form_button_save"));

        // checkbox 'Hide in Kanban'
        const badgeElement = target.querySelectorAll(".o_field_many2many_tags .badge")[1]; // selects 'red' tag
        await click(badgeElement);
        assert.containsOnce(
            target,
            ".o_tag_popover .custom-checkbox input",
            "should have a checkbox in the colorpicker popover"
        );

        let checkBox = target.querySelector(".o_tag_popover .custom-checkbox input");
        assert.notOk(checkBox.checked, "should have unticked checkbox in colorpicker popover");

        await click(target, ".o_tag_popover input[type='checkbox']");

        assert.strictEqual(
            badgeElement.dataset.color,
            "0",
            "should become white/transparent when toggling on checkbox"
        );

        await click(badgeElement);
        checkBox = target.querySelector(".o_tag_popover .custom-checkbox input"); // refresh

        assert.ok(
            checkBox.checked,
            "should have a ticked checkbox in colorpicker popover after mousedown"
        );

        await click(target, ".o_tag_popover input[type='checkbox']");

        assert.strictEqual(
            badgeElement.dataset.color,
            "8",
            "should revert to old color when toggling off checkbox"
        );

        await click(badgeElement);
        checkBox = target.querySelector(".o_tag_popover .custom-checkbox input"); // refresh

        assert.notOk(
            checkBox.checked,
            "should have an unticked checkbox in colorpicker popover after 2nd click"
        );
    });

    QUnit.test("fieldmany2many tags in tree view", async function (assert) {
        assert.expect(4);

        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `<tree>
                    <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                    <field name="foo"/>
                </tree>`,
            selectRecord: () => {
                assert.step("selectRecord");
            },
        });

        assert.containsN(target, ".o_field_many2many_tags .badge", 2, "there should be 2 tags");
        assert.containsNone(target, ".badge.dropdown-toggle", "the tags should not be dropdowns");

        // click on the tag: should do nothing and open the form view
        click(target.querySelector(".o_field_many2many_tags .badge :nth-child(1)"));

        assert.verifySteps(["selectRecord"]);
    });

    QUnit.test("fieldmany2many tags view a domain", async function (assert) {
        assert.expect(7);

        serverData.models.partner.fields.timmy.domain = [["id", "<", 50]];
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records.push({ id: 99, display_name: "red", color: 8 });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                    <field name="timmy" widget="many2many_tags" options="{'no_create_edit': True}"/>
                </form>`,
            resId: 1,
            mockRPC: (route, args, performRPC) => {
                if (args.method === "name_search") {
                    assert.deepEqual(
                        args.kwargs.args,
                        ["&", ["id", "<", 50], "!", ["id", "in", [12]]],
                        "domain sent to name_search should be correct"
                    );
                }
                return performRPC(route, args);
            },
        });

        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain 1 tag");
        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".badge")),
            "gold",
            "should have fetched and rendered gold partner tag"
        );

        await clickEdit(target);

        await clickDropdown(target, "timmy");

        const autocompleteDropdown = target.querySelector(".o-autocomplete--dropdown-menu");

        assert.strictEqual(
            autocompleteDropdown.querySelectorAll("li").length,
            2,
            "autocomplete dropdown should have 2 entry"
        );

        assert.strictEqual(
            autocompleteDropdown.querySelector("li a").textContent,
            "silver",
            "autocomplete dropdown should contain 'silver'"
        );

        await clickOpenedDropdownItem(target, "timmy", "silver");

        assert.strictEqual(
            target.querySelectorAll(".o_field_many2many_tags .badge").length,
            2,
            "should contain 2 tags"
        );

        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".badge")),
            "goldsilver",
            "should contain newly added tag 'silver'"
        );
    });

    QUnit.test("fieldmany2many tags in a new record", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            mockRPC: (route, { args }) => {
                if (route === "/web/dataset/call_kw/partner/create") {
                    var commands = args[0].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(
                        commands[0][0],
                        6,
                        "generated command should be REPLACE WITH"
                    );
                    assert.ok(_.isEqual(commands[0][2], [12]), "new value should be [12]");
                }
            },
        });
        assert.strictEqual(
            target.querySelectorAll(".o_form_view .o_form_editable").length,
            1,
            "form should be in edit mode"
        );

        await clickDropdown(target, "timmy");
        const autocomplete = target.querySelector("[name='timmy'] .o-autocomplete.dropdown");
        assert.strictEqual(
            autocomplete.querySelectorAll("li").length,
            3,
            "autocomplete dropdown should have 3 entries (2 values + 'Search and Edit...')"
        );
        await clickOpenedDropdownItem(target, "timmy", "gold");

        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain 1 tag");
        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".o_field_many2many_tags .badge")),
            "gold",
            "should contain newly added tag 'gold'"
        );

        // save the record (should do the write RPC with the correct commands)
        await clickSave(target);
    });

    QUnit.test("fieldmany2many tags: update color", async function (assert) {
        assert.expect(6);

        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records[0].color = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/></form>`,
            mockRPC: (route, { args, method }) => {
                if (method === "write") {
                    assert.step(JSON.stringify(args[1]));
                }
            },
            resId: 1,
        });

        // First checks that default color 0 is rendered as 0 color
        let badgeNode = target.querySelector(".o_tag.badge");
        assert.strictEqual(badgeNode.dataset.color, "0", "first tag color should be 0");

        // Update the color in readonly => write automatically
        await click(badgeNode);
        await click(target, '.o_colorlist button[data-color="1"]');
        assert.strictEqual(
            badgeNode.dataset.color,
            "1",
            "should have correctly updated the color (in readonly)"
        );

        // Update the color in edit => write on save with rest of the record
        await clickEdit(target);
        await click(badgeNode);
        await click(target, '.o_colorlist button[data-color="6"]');
        await nextTick();
        assert.strictEqual(
            badgeNode.dataset.color,
            "6",
            "should have correctly updated the color (in edit)"
        );

        // TODO POST WOWL GES: commented code below is to make the m2mtags more.
        // consistent. No color change if edit => discard.
        // await clickSave(target);

        assert.verifySteps([
            `{"color":1}`,
            `{"color":6}`,
            //  `{"timmy":[[1,12,{"color":6}]]}`
        ]);

        /*
        badgeNode = target.querySelector(".o_tag.badge"); // need to refresh the reference

        // Update the color in edit without save => we don't go through RPC
        // so it's not saved and it is lost on discard.
        await clickEdit(target);
        await click(badgeNode);
        await click(target, '.o_colorlist button[data-color="8"]');
        await nextTick();
        assert.strictEqual(
            badgeNode.dataset.color,
            "8",
            "should have correctly updated the color (in edit)"
        );

        await clickDiscard(target);

        assert.strictEqual(
            badgeNode.dataset.color,
            "6",
            "should have correctly cancel the color update"
        );

        */
    });

    QUnit.test("fieldmany2many tags with no_edit_color option", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags" options="{'color_field': 'color', 'no_edit_color': 1}"/></form>`,
            resId: 1,
        });

        // Click to try to open colorpicker
        await click(target.querySelector(".o_tag.badge"));
        assert.containsNone(target, ".o_colorlist");
    });

    QUnit.test("fieldmany2many tags in editable list", async function (assert) {
        assert.expect(7);

        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            context: { take: "five" },
            arch: `<tree editable="bottom">
                    <field name="timmy" widget="many2many_tags" />
                </tree>`,
            mockRPC: (route, { kwargs, method, model }) => {
                if (method === "read" && model === "partner_type") {
                    assert.strictEqual(
                        kwargs.context.take,
                        "five",
                        "The context should be passed to the RPC"
                    );
                }
            },
        });

        const firstRow = target.querySelectorAll(".o_data_row")[0];
        const m2mTagsCell = firstRow.querySelector(".o_many2many_tags_cell");

        assert.containsOnce(
            firstRow,
            ".o_field_many2many_tags .badge",
            "m2m field should contain one tag"
        );

        // edit first row
        await click(m2mTagsCell);

        assert.containsOnce(
            m2mTagsCell,
            ".o_field_many2many_selection",
            "a many2one widget should have been instantiated"
        );

        // add a tag
        await selectDropdownItem(firstRow, "timmy", "silver");

        assert.containsN(
            firstRow,
            ".o_field_many2many_tags .badge",
            2,
            "m2m field should contain 2 tags"
        );

        await clickSave(target);

        assert.containsN(
            firstRow,
            ".o_field_many2many_tags .badge",
            2,
            "m2m field should contain 2 tags"
        );
    });

    QUnit.test("many2many_tags can load more than 40 records", async function (assert) {
        assert.expect(1);

        serverData.models.partner.fields.partner_ids = {
            string: "Partner",
            type: "many2many",
            relation: "partner",
        };
        serverData.models.partner.records[0].partner_ids = [];
        for (var i = 15; i < 115; i++) {
            serverData.models.partner.records.push({ id: i, display_name: "walter" + i });
            serverData.models.partner.records[0].partner_ids.push(i);
        }
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
            resId: 1,
        });
        assert.containsN(
            target,
            '.o_field_widget[name="partner_ids"] .badge',
            100,
            "should have rendered 100 tags"
        );
    });

    QUnit.test(
        "many2many_tags loads records according to limit defined on widget prototype",
        async function (assert) {
            assert.expect(1);

            patchWithCleanup(Many2ManyTagsField, {
                limit: 30,
            });

            serverData.models.partner.fields.partner_ids = {
                string: "Partner",
                type: "many2many",
                relation: "partner",
            };
            serverData.models.partner.records[0].partner_ids = [];
            for (var i = 15; i < 50; i++) {
                serverData.models.partner.records.push({ id: i, display_name: "walter" + i });
                serverData.models.partner.records[0].partner_ids.push(i);
            }
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="partner_ids" widget="many2many_tags"/></form>',
                resId: 1,
            });

            assert.strictEqual(
                target.querySelectorAll('.o_field_widget[name="partner_ids"] .badge').length,
                30,
                "should have rendered 30 tags even though 35 records linked"
            );
        }
    );

    QUnit.test("field many2many_tags keeps focus when being edited", async function (assert) {
        assert.expect(7);

        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner.onchanges.foo = function (obj) {
            obj.timmy = [[5]]; // DELETE command
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                    <field name="foo"/>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
            resId: 1,
        });

        await clickEdit(target);
        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain one tag");

        // update foo, which will trigger an onchange and update timmy
        // -> m2mtags input should not have taken the focus
        const textInput = target.querySelector("[name=foo] input");
        textInput.focus();
        await editInput(textInput, null, "trigger onchange");
        assert.containsNone(target, ".o_field_many2many_tags .badge", "should contain no tags");
        assert.strictEqual(
            textInput,
            document.activeElement,
            "foo input should have kept the focus"
        );

        await selectDropdownItem(target, "timmy", "gold");
        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain a tag");
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags input"),
            document.activeElement,
            "m2m tags input should have kept the focus"
        );

        // remove a tag -> m2mtags input should still have the focus
        await click(target.querySelector(".o_field_many2many_tags .o_delete"));
        assert.containsNone(target, ".o_field_many2many_tags .badge", "should contain no tags");
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags input"),
            document.activeElement,
            "m2m tags input should have kept the focus"
        );
    });

    QUnit.test("widget many2many_tags: tags title attribute", async function (assert) {
        assert.expect(1);
        serverData.models.turtle.records[0].partner_ids = [2];

        await makeView({
            type: "form",
            serverData,
            resModel: "turtle",
            resId: 1,
            arch: `<form string="Turtles">
                    <sheet>
                        <field name="display_name"/>
                        <field name="partner_ids" widget="many2many_tags"/>
                    </sheet>
                </form>`,
        });

        assert.deepEqual(
            target.querySelector(".o_field_many2many_tags .o_tag.badge").title,
            "second record",
            "the title should be filled in"
        );
    });

    QUnit.test(
        "widget many2many_tags: toggle colorpicker with multiple tags",
        async function (assert) {
            serverData.models.partner.records[0].timmy = [12, 14];
            serverData.models.partner_type.records[0].color = 0;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `<form>
                        <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                    </form>`,
                resId: 1,
            });

            assert.containsNone(target, ".o_colorpicker", "colorpicker should be closed");

            // click on the badge to open colorpicker
            await click(target.querySelector(".o_field_many2many_tags .badge"));
            assert.containsOnce(target, ".o_colorlist", "colorpicker should be open");

            await click(target.querySelector(".o_field_many2many_tags [title=silver]"));
            assert.containsOnce(target, ".o_colorlist", "only one colorpicker should be open");

            await click(target.querySelector(".o_field_many2many_tags [title=silver]"));
            assert.containsNone(target, ".o_colorpicker", "colorpicker should be closed");

            await click(target.querySelector(".o_field_many2many_tags [title=silver]"));
            assert.containsOnce(target, ".o_colorlist", "colorpicker should be open");

            await click(target);
            assert.containsNone(
                target,
                ".o_colorpicker",
                "click outside should close the colorpicker"
            );
        }
    );

    QUnit.test("widget many2many_tags: toggle colorpicker multiple times", async function (assert) {
        assert.expect(11);

        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records[0].color = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form>
                        <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                    </form>`,
            resId: 1,
        });

        await clickEdit(target);

        assert.strictEqual(
            target.querySelectorAll(".o_field_many2many_tags .badge").length,
            1,
            "should have one tag"
        );
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .badge").dataset.color,
            "0",
            "tag should have color 0"
        );
        assert.containsNone(target, ".o_colorpicker", "colorpicker should be closed");

        // click on the badge to open colorpicker
        await click(target.querySelector(".o_field_many2many_tags .badge"));

        assert.containsOnce(target, ".o_colorlist", "colorpicker should be open");

        // click on the badge again to close colorpicker
        await click(target.querySelector(".o_field_many2many_tags .badge"));

        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .badge").dataset.color,
            "0",
            "tag should still have color 0"
        );
        assert.containsNone(target, ".o_colorlist", "colorpicker should be closed");

        // click on the badge to open colorpicker
        await click(target.querySelector(".o_field_many2many_tags .badge"));

        assert.containsOnce(target, ".o_colorlist", "colorpicker should be open");

        // click on the colorpicker, but not on a color
        await click(target.querySelector(".o_colorlist"));

        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .badge").dataset.color,
            "0",
            "tag should still have color 0"
        );
        assert.containsOnce(target, ".o_colorlist", "colorpicker should not be closed");

        await click(target, '.o_colorlist button[data-color="2"]');

        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .badge").dataset.color,
            "2",
            "tag should have color 2"
        );
        assert.containsNone(target, ".o_colorlist", "colorpicker should be closed");
    });

    QUnit.test("fieldmany2many tags: quick create a new record", async function (assert) {
        assert.expect(3);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
        });

        assert.containsNone(target, ".o_field_many2many_tags .badge");

        await editInput(
            target.querySelector(".o_field_many2many_selection .o_input_dropdown input"),
            null,
            "new"
        );
        await selectDropdownItem(target, "timmy", `Create "new"`);

        assert.containsOnce(target, ".o_field_many2many_tags .badge");

        await click(target.querySelector(".o_form_button_save"));

        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags").textContent.trim(),
            "new"
        );
    });

    QUnit.test("select a many2many value by focusing out", async function (assert) {
        assert.expect(5);

        serverData.models.partner_type.records.push({ id: 13, display_name: "red", color: 8 });

        patchWithCleanup(AutoComplete, {
            timeout: 0,
        });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
        });

        assert.containsNone(target, ".o_field_many2many_tags .badge");
        let input = target.querySelector(".o_field_many2many_tags input");
        await triggerEvent(input, null, "focus");
        await click(input);
        await editInput(input, null, "go");
        await triggerEvent(input, null, "blur");

        assert.containsNone(document.body, ".modal");
        assert.containsOnce(target, ".o_field_many2many_tags .badge");
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .badge").textContent,
            "gold"
        );

        input = target.querySelector(".o_field_many2many_tags input");
        await triggerEvent(input, null, "focus");
        await click(input);
        await editInput(input, null, "r");
        await triggerEvent(input, null, "keydown", { key: "ArrowDown" });
        await triggerEvent(input, null, "blur");
        assert.strictEqual(
            target.querySelectorAll(".o_field_many2many_tags .badge")[1].textContent,
            "red",
            "the second element in the list has been selected"
        );
    });

    QUnit.test("widget many2many_tags in one2many with display_name", async function (assert) {
        serverData.models.turtle.records[0].partner_ids = [2];
        serverData.views = {
            "partner,false,list": '<tree><field name="foo"/></tree>',
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="turtles">
                        <tree>
                            <field name="partner_ids" widget="many2many_tags"/>
                        </tree>
                        <form>
                            <field name="partner_ids"/>
                        </form>
                    </field>
                </form>
            `,
            resId: 1,
        });

        await clickEdit(target);
        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            "second recordaaa",
            "the tags should be correctly rendered"
        );

        // open the x2m form view
        await click(target.querySelector('.o_field_one2many[name="turtles"] .o_data_cell'));
        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".modal .o_data_cell")),
            "blipMy little Foo Value",
            "the list view should be correctly rendered with foo"
        );

        await click(target.querySelector(".modal button.o_form_button_cancel"));
        assert.strictEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            "second recordaaa",
            "the tags should still be correctly rendered"
        );
    });

    QUnit.test("many2many read, field context is properly sent", async function (assert) {
        assert.expect(4);

        serverData.models.partner.fields.timmy.context = { hello: "world" };
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "read" && args.model === "partner_type") {
                    assert.step(args.kwargs.context.hello);
                }
            },
        });

        assert.verifySteps(["world"]);
        await clickEdit(target);
        await selectDropdownItem(target, "timmy", "silver");
        assert.verifySteps(["world"]);
    });

    QUnit.skipWOWL("widget many2many_tags", async function (assert) {
        assert.expect(1);
        serverData.models.turtle.records[0].partner_ids = [2];

        await makeView({
            type: "form",
            resModel: "turtle",
            serverData,
            arch:
                '<form string="Turtles">' +
                "<sheet>" +
                '<field name="display_name"/>' +
                '<field name="partner_ids" widget="many2many_tags"/>' +
                "</sheet>" +
                "</form>",
            resId: 1,
        });

        assert.deepEqual(
            $(target)
                .find(".o_field_many2manytags.o_field_widget .badge .o_badge_text")
                .attr("title"),
            "second record",
            "the title should be filled in"
        );
    });

    QUnit.skipWOWL("many2many tags widget: select multiple records", async function (assert) {
        assert.expect(5);
        for (var i = 1; i <= 10; i++) {
            this.data.partner_type.records.push({ id: 100 + i, display_name: "Partner" + i });
        }
        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch:
                '<form string="Partners">' +
                '<field name="display_name"/>' +
                '<field name="timmy" widget="many2many_tags"/>' +
                "</form>",
            res_id: 1,
            archs: {
                "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                "partner_type,false,search": '<search><field name="display_name"/></search>',
            },
        });
        await testUtils.form.clickEdit(form);
        await testUtils.fields.many2one.clickOpenDropdown("timmy");
        await testUtils.fields.many2one.clickItem("timmy", "Search More");
        assert.ok($(".modal .o_list_view"), "should have open the modal");

        // + 1 for the select all
        assert.containsN(
            $(document),
            ".modal .o_list_view .o_list_record_selector input",
            this.data.partner_type.records.length + 1,
            "Should have record selector checkboxes to select multiple records"
        );
        //multiple select tag
        await testUtils.dom.click($(".modal .o_list_view thead .o_list_record_selector input"));
        assert.ok(
            !$(".modal .o_select_button").prop("disabled"),
            "select button should be enabled"
        );
        await testUtils.dom.click($(".o_select_button"));
        assert.containsNone($(document), ".modal .o_list_view", "should have closed the modal");
        assert.containsN(
            form,
            '.o_field_many2manytags[name="timmy"] .badge',
            this.data.partner_type.records.length,
            "many2many tag should now contain 12 records"
        );
        form.destroy();
    });

    QUnit.skipWOWL(
        "many2many tags widget: select multiple records doesn't show already added tags",
        async function (assert) {
            assert.expect(5);
            for (var i = 1; i <= 10; i++) {
                this.data.partner_type.records.push({ id: 100 + i, display_name: "Partner" + i });
            }
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                    "</form>",
                res_id: 1,
                archs: {
                    "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                    "partner_type,false,search": '<search><field name="display_name"/></search>',
                },
            });
            await testUtils.form.clickEdit(form);

            await testUtils.fields.many2one.clickOpenDropdown("timmy");
            await testUtils.fields.many2one.clickItem("timmy", "Partner1");

            await testUtils.fields.many2one.clickOpenDropdown("timmy");
            await testUtils.fields.many2one.clickItem("timmy", "Search More");
            assert.ok($(".modal .o_list_view"), "should have open the modal");

            // -1 for the one that is already on the form & +1 for the select all,
            assert.containsN(
                $(document),
                ".modal .o_list_view .o_list_record_selector input",
                this.data.partner_type.records.length - 1 + 1,
                "Should have record selector checkboxes to select multiple records"
            );
            //multiple select tag
            await testUtils.dom.click($(".modal .o_list_view thead .o_list_record_selector input"));
            assert.ok(
                !$(".modal .o_select_button").prop("disabled"),
                "select button should be enabled"
            );
            await testUtils.dom.click($(".o_select_button"));
            assert.containsNone($(document), ".modal .o_list_view", "should have closed the modal");
            assert.containsN(
                form,
                '.o_field_many2manytags[name="timmy"] .badge',
                this.data.partner_type.records.length,
                "many2many tag should now contain 12 records"
            );
            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "many2many tags widget: save&new in edit mode doesn't close edit window",
        async function (assert) {
            assert.expect(5);
            for (var i = 1; i <= 10; i++) {
                this.data.partner_type.records.push({ id: 100 + i, display_name: "Partner" + i });
            }
            var form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch:
                    '<form string="Partners">' +
                    '<field name="display_name"/>' +
                    '<field name="timmy" widget="many2many_tags"/>' +
                    "</form>",
                res_id: 1,
                archs: {
                    "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                    "partner_type,false,search": '<search><field name="display_name"/></search>',
                    "partner_type,false,form": '<form><field name="display_name"/></form>',
                },
            });
            await testUtils.form.clickEdit(form);

            await testUtils.fields.many2one.createAndEdit("timmy", "Ralts");
            assert.containsOnce($(document), ".modal .o_form_view", "should have opened the modal");

            // Create multiple records with save & new
            await testUtils.fields.editInput($(".modal input:first"), "Ralts");
            await testUtils.dom.click($(".modal .btn-primary:nth-child(2)"));
            assert.containsOnce($(document), ".modal .o_form_view", "modal should still be open");
            assert.equal($(".modal input:first")[0].value, "", "input should be empty");

            // Create another record and click save & close
            await testUtils.fields.editInput($(".modal input:first"), "Pikachu");
            await testUtils.dom.click($(".modal .btn-primary:first"));
            assert.containsNone($(document), ".modal .o_list_view", "should have closed the modal");
            assert.containsN(
                form,
                '.o_field_many2manytags[name="timmy"] .badge',
                2,
                "many2many tag should now contain 2 records"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "many2many tags widget: make tag name input field blank on Save&New",
        async function (assert) {
            assert.expect(4);

            let onchangeCalls = 0;
            const form = await createView({
                View: FormView,
                model: "partner",
                data: this.data,
                arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
                archs: {
                    "partner_type,false,form": '<form><field name="name"/></form>',
                },
                res_id: 1,
                mockRPC: function (route, args) {
                    if (args.method === "onchange") {
                        if (onchangeCalls === 0) {
                            assert.deepEqual(
                                args.kwargs.context,
                                { default_name: "hello" },
                                "context should have default_name with 'hello' as value"
                            );
                        }
                        if (onchangeCalls === 1) {
                            assert.deepEqual(
                                args.kwargs.context,
                                {},
                                "context should have default_name with false as value"
                            );
                        }
                        onchangeCalls++;
                    }
                    return this._super.apply(this, arguments);
                },
            });

            await testUtils.form.clickEdit(form);

            await testUtils.fields.editInput($(".o_field_widget input"), "hello");
            await testUtils.fields.many2one.clickItem("timmy", "Create and Edit");
            assert.strictEqual(
                document.querySelector(".modal .o_form_view input").value,
                "hello",
                "should contain the 'hello' in the tag name input field"
            );

            // Create record with save & new
            await testUtils.dom.click(document.querySelector(".modal .btn-primary:nth-child(2)"));
            assert.strictEqual(
                document.querySelector(".modal .o_form_view input").value,
                "",
                "should display the blank value in the tag name input field"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL(
        "many2many_tags widget: conditional create/delete actions",
        async function (assert) {
            assert.expect(10);

            this.data.turtle.records[0].partner_ids = [2];
            for (var i = 1; i <= 10; i++) {
                this.data.partner.records.push({ id: 100 + i, display_name: "Partner" + i });
            }

            const form = await createView({
                View: FormView,
                model: "turtle",
                data: this.data,
                arch: `
                <form>
                    <field name="display_name"/>
                    <field name="turtle_bar"/>
                    <field name="partner_ids" options="{'create': [('turtle_bar', '=', True)], 'delete': [('turtle_bar', '=', True)]}" widget="many2many_tags"/>
                </form>`,
                archs: {
                    "partner,false,list": '<tree><field name="name"/></tree>',
                    "partner,false,search": "<search/>",
                },
                res_id: 1,
                viewOptions: {
                    mode: "edit",
                },
            });

            // turtle_bar is true -> create and delete actions are available
            assert.containsOnce(
                form,
                ".o_field_many2manytags.o_field_widget .badge .o_delete",
                "X icon on badges should not be available"
            );

            await testUtils.fields.many2one.clickOpenDropdown("partner_ids");

            const $dropdown1 = form.$(".o_field_many2one input").autocomplete("widget");
            assert.containsOnce(
                $dropdown1,
                "li.o_m2o_start_typing:contains(Start typing...)",
                "autocomplete should contain Start typing..."
            );

            await testUtils.fields.many2one.clickItem("partner_ids", "Search More");

            assert.containsN(
                document.body,
                ".modal .modal-footer button",
                3,
                "there should be 3 buttons (Select, Create and Cancel) available in the modal footer"
            );

            await testUtils.dom.click($(".modal .modal-footer .o_form_button_cancel"));

            // type something that doesn't exist
            await testUtils.fields.editAndTrigger(
                form.$(".o_field_many2one input"),
                "Something that does not exist",
                "keydown"
            );
            // await testUtils.nextTick();
            assert.containsN(
                form.$(".o_field_many2one input").autocomplete("widget"),
                "li.o_m2o_dropdown_option",
                2,
                "autocomplete should contain Create and Create and Edit... options"
            );

            // set turtle_bar false -> create and delete actions are no longer available
            await testUtils.dom.click(form.$('.o_field_widget[name="turtle_bar"] input').first());

            // remove icon should still be there as it doesn't delete records but rather remove links
            assert.containsOnce(
                form,
                ".o_field_many2manytags.o_field_widget .badge .o_delete",
                "X icon on badge should still be there even after turtle_bar is not checked"
            );

            await testUtils.fields.many2one.clickOpenDropdown("partner_ids");
            const $dropdown2 = form.$(".o_field_many2one input").autocomplete("widget");

            // only Search More option should be available
            assert.containsOnce(
                $dropdown2,
                "li.o_m2o_dropdown_option",
                "autocomplete should contain only one option"
            );
            assert.containsOnce(
                $dropdown2,
                "li.o_m2o_dropdown_option:contains(Search More)",
                "autocomplete option should be Search More"
            );

            await testUtils.fields.many2one.clickItem("partner_ids", "Search More");

            assert.containsN(
                document.body,
                ".modal .modal-footer button",
                2,
                "there should be 2 buttons (Select and Cancel) available in the modal footer"
            );

            await testUtils.dom.click($(".modal .modal-footer .o_form_button_cancel"));

            // type something that doesn't exist
            await testUtils.fields.editAndTrigger(
                form.$(".o_field_many2one input"),
                "Something that does not exist",
                "keyup"
            );
            // await testUtils.nextTick();

            // only Search More option should be available
            assert.containsOnce(
                $dropdown2,
                "li.o_m2o_dropdown_option",
                "autocomplete should contain only one option"
            );
            assert.containsOnce(
                $dropdown2,
                "li.o_m2o_dropdown_option:contains(Search More)",
                "autocomplete option should be Search More"
            );

            form.destroy();
        }
    );

    QUnit.skipWOWL("failing many2one quick create in a many2many_tags", async function (assert) {
        assert.expect(5);

        var form = await createView({
            View: FormView,
            model: "partner",
            data: this.data,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    return Promise.reject();
                }
                if (args.method === "create") {
                    assert.deepEqual(args.args[0], {
                        color: 8,
                        name: "new partner",
                    });
                }
                return this._super.apply(this, arguments);
            },
            archs: {
                "partner_type,false,form": `
                    <form>
                        <field name="name"/>
                        <field name="color"/>
                    </form>`,
            },
        });

        assert.containsNone(form, ".o_field_many2manytags .badge");

        // try to quick create a record
        await testUtils.dom.triggerEvent(form.$(".o_field_many2one input"), "focus");
        await testUtils.fields.many2one.searchAndClickItem("timmy", {
            search: "new partner",
            item: "Create",
        });

        // as the quick create failed, a dialog should be open to 'slow create' the record
        assert.containsOnce(document.body, ".modal .o_form_view");
        assert.strictEqual($(".modal .o_field_widget[name=name]").val(), "new partner");

        await testUtils.fields.editInput($(".modal .o_field_widget[name=color]"), 8);
        await testUtils.modal.clickButton("Save & Close");

        assert.containsOnce(form, ".o_field_many2manytags .badge");

        form.destroy();
    });
});
