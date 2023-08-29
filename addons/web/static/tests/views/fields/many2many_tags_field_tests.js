/** @odoo-module **/

import { makeServerError } from "@web/../tests/helpers/mock_server";
import { AutoComplete } from "@web/core/autocomplete/autocomplete";
import { browser } from "@web/core/browser/browser";
import {
    click,
    clickDiscard,
    clickDropdown,
    clickOpenedDropdownItem,
    clickSave,
    editInput,
    getFixture,
    getNodesTextContent,
    makeDeferred,
    nextTick,
    patchWithCleanup,
    selectDropdownItem,
    triggerEvent,
    triggerHotkey,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

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
                        turtles: {
                            string: "one2many turtle field",
                            type: "one2many",
                            relation: "turtle",
                            relation_field: "turtle_trululu",
                        },
                        timmy: { string: "pokemon", type: "many2many", relation: "partner_type" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first record",
                            foo: "yop",
                            turtles: [2],
                            timmy: [],
                        },
                        {
                            id: 2,
                            display_name: "second record",
                            foo: "blip",
                            timmy: [],
                        },
                        {
                            id: 4,
                            display_name: "aaa",
                        },
                    ],
                    onchanges: {},
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
                        turtle_bar: { string: "Bar", type: "boolean", default: true },
                        partner_ids: { string: "Partner", type: "many2many", relation: "partner" },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "leonardo",
                            turtle_bar: true,
                            partner_ids: [],
                        },
                        {
                            id: 2,
                            display_name: "donatello",
                            turtle_bar: true,
                            partner_ids: [2, 4],
                        },
                        {
                            id: 3,
                            display_name: "raphael",
                            turtle_bar: false,
                            partner_ids: [],
                        },
                    ],
                    onchanges: {},
                },
            },
        };

        setupViewRegistries();
        patchWithCleanup(browser, {
            setTimeout: (fn) => Promise.resolve().then(fn),
        });
    });

    QUnit.module("Many2ManyTagsField");

    QUnit.test("Many2ManyTagsField with and without color", async function (assert) {
        assert.expect(14);

        serverData.models.partner.fields.partner_ids = {
            string: "Partner",
            type: "many2many",
            relation: "partner",
        };
        serverData.models.partner.fields.color = { string: "Color index", type: "integer" };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="partner_ids" widget="many2many_tags" options="{'color_field': 'color'}"/>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
            mockRPC: (route, { args, method, model, kwargs }) => {
                if (method === "web_read" && model === "partner_type") {
                    assert.deepEqual(args, [[12]]);
                    assert.deepEqual(
                        kwargs.specification,
                        { display_name: {} },
                        "should not read any color field"
                    );
                } else if (method === "web_read" && model === "partner") {
                    assert.deepEqual(args, [[1]]);
                    assert.deepEqual(
                        kwargs.specification,
                        { display_name: {}, color: {} },
                        "should read color field"
                    );
                }
            },
        });

        // Add a tag to first field
        assert.containsNone(target, "[name=partner_ids] .o_tag");
        await selectDropdownItem(target, "partner_ids", "first record");
        assert.containsOnce(target, "[name=partner_ids] .o_tag");

        // Show the color list
        assert.containsNone(target, ".o_colorlist");
        await click(target, "[name=partner_ids] .o_tag");
        assert.containsOnce(target, ".o_colorlist");

        // Add a tag to second field
        assert.containsNone(target, "[name=timmy] .o_tag");
        await clickDropdown(target, "timmy");
        const autocomplete = target.querySelector("[name='timmy'] .o-autocomplete.dropdown");
        assert.strictEqual(
            autocomplete.querySelectorAll("li").length,
            4,
            "autocomplete dropdown should have 4 entries (2 values + 'Search More...' + 'Search and Edit...')"
        );
        await clickOpenedDropdownItem(target, "timmy", "gold");
        assert.containsOnce(target, "[name=timmy] .o_tag");
        assert.deepEqual(
            getNodesTextContent(
                target.querySelectorAll(`.o_field_many2many_tags[name="timmy"] .badge`)
            ),
            ["gold"]
        );

        // Show the color list
        assert.containsNone(target, ".o_colorlist");
        await click(target, "[name=timmy] .o_tag");
        assert.containsNone(target, ".o_colorlist");
    });

    QUnit.test("Many2ManyTagsField with color: rendering and edition", async function (assert) {
        assert.expect(24);

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
            mockRPC: (route, { args, method, model, kwargs }) => {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    var commands = args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(
                        commands[0][0],
                        6,
                        "generated command should be REPLACE WITH"
                    );
                    assert.deepEqual(commands[0][2], [12, 13], "new value should be [12, 13]");
                }
                if ((method === "web_read" || method === "web_save") && model === "partner_type") {
                    assert.deepEqual(
                        kwargs.specification,
                        { display_name: {}, color: {} },
                        "should read color field"
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
            3,
            "autocomplete dropdown should have 3 entry"
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
        await clickSave(target);

        // checkbox 'Hide in Kanban'
        const badgeElement = target.querySelectorAll(".o_field_many2many_tags .badge")[1]; // selects 'red' tag
        await click(badgeElement);
        assert.containsOnce(
            target,
            ".o_tag_popover .form-check input",
            "should have a checkbox in the colorpicker popover"
        );

        let checkBox = target.querySelector(".o_tag_popover .form-check input");
        assert.notOk(checkBox.checked, "should have unticked checkbox in colorpicker popover");

        await click(target, ".o_tag_popover input[type='checkbox']");

        assert.strictEqual(
            badgeElement.dataset.color,
            "0",
            "should become white/transparent when toggling on checkbox"
        );

        await click(badgeElement);
        checkBox = target.querySelector(".o_tag_popover .form-check input"); // refresh

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
        checkBox = target.querySelector(".o_tag_popover .form-check input"); // refresh

        assert.notOk(
            checkBox.checked,
            "should have an unticked checkbox in colorpicker popover after 2nd click"
        );
    });

    QUnit.test("Many2ManyTagsField in tree view", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree>
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
        await nextTick();

        assert.containsNone(target, ".o_colorlist");

        await click(target.querySelectorAll(".o_list_record_selector")[1]);
        click(target.querySelector(".o_field_many2many_tags .badge :nth-child(1)"));
        assert.verifySteps(["selectRecord"]);
        await nextTick();

        assert.containsNone(target, ".o_colorlist");
    });

    QUnit.test("Many2ManyTagsField in tree view -- multi edit", async function (assert) {
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree multi_edit="1">
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
        await nextTick();

        assert.containsNone(target, ".o_colorlist");

        await click(target.querySelectorAll(".o_list_record_selector")[1]);
        click(target.querySelector(".o_field_many2many_tags .badge :nth-child(1)"));
        assert.verifySteps([]);
        await nextTick();

        assert.containsOnce(target, ".o_selected_row");
        assert.containsNone(target, ".o_colorlist");
    });

    QUnit.test("Many2ManyTagsField view a domain", async function (assert) {
        assert.expect(7);

        serverData.models.partner.fields.timmy.domain = [["id", "<", 50]];
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records.push({ id: 99, display_name: "red", color: 8 });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'no_create_edit': True}"/>
                </form>`,
            resId: 1,
            mockRPC: (route, args) => {
                if (args.method === "name_search") {
                    assert.deepEqual(
                        args.kwargs.args,
                        ["&", ["id", "<", 50], "!", ["id", "in", [12]]],
                        "domain sent to name_search should be correct"
                    );
                }
            },
        });

        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain 1 tag");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".badge")),
            ["gold"],
            "should have fetched and rendered gold partner tag"
        );

        await clickDropdown(target, "timmy");

        const autocompleteDropdown = target.querySelector(".o-autocomplete--dropdown-menu");

        assert.strictEqual(
            autocompleteDropdown.querySelectorAll("li").length,
            3,
            "autocomplete dropdown should have 3 entries"
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

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".badge")),
            ["gold", "silver"],
            "should contain newly added tag 'silver'"
        );
    });

    QUnit.test("use binary field as the domain", async (assert) => {
        serverData.models.partner.fields.domain = { string: "Domain", type: "binary" };
        serverData.models.partner.records[0].domain = [["id", "<", 50]];
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records.push({ id: 99, display_name: "red", color: 8 });

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" domain="domain"/>
                    <field name="domain" invisible="1"/>
                </form>`,
            resId: 1,
        });

        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain 1 tag");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".badge")),
            ["gold"],
            "should have fetched and rendered gold partner tag"
        );

        await clickDropdown(target, "timmy");

        const autocompleteDropdown = target.querySelector(".o-autocomplete--dropdown-menu");

        assert.strictEqual(
            autocompleteDropdown.querySelectorAll("li").length,
            3,
            "autocomplete dropdown should have 3 entries"
        );
        assert.deepEqual(
            getNodesTextContent(autocompleteDropdown.querySelectorAll("li")),
            ["silver", "Search More...", "Start typing..."],
            "should contain newly added tag 'silver'"
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
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".badge")),
            ["gold", "silver"],
            "should contain newly added tag 'silver'"
        );
    });

    QUnit.test("Domain: allow python code domain in fieldInfo", async function (assert) {
        assert.expect(4);
        serverData.models.partner.fields.timmy.domain =
            "foo and [('color', '>', 3)] or [('color', '<', 3)]";
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="timmy" widget="many2many_tags"></field>
                </form>`,
            resId: 1,
        });

        // foo set => only silver (id=5) selectable
        await clickDropdown(target, "timmy");
        let autocompleteDropdown = target.querySelector(".o-autocomplete--dropdown-menu");
        assert.containsN(
            autocompleteDropdown,
            "li",
            3,
            "autocomplete should contain 'silver'm 'Search More...' and 'Start typing...' options"
        );
        assert.strictEqual(
            autocompleteDropdown.querySelector("li a").textContent,
            "silver",
            "autocomplete dropdown should contain 'silver'"
        );
        await clickOpenedDropdownItem(target, "timmy", "Start typing...");

        // set foo = "" => only gold (id=2) selectable
        const textInput = target.querySelector("[name=foo] input");
        textInput.focus();
        await editInput(textInput, null, "");
        await clickDropdown(target, "timmy");
        autocompleteDropdown = target.querySelector(".o-autocomplete--dropdown-menu");
        assert.containsN(
            autocompleteDropdown,
            "li",
            3,
            "autocomplete should contain 'gold'm 'Search More...' and 'Start typing...' options"
        );
        assert.strictEqual(
            autocompleteDropdown.querySelector("li a").textContent,
            "gold",
            "autocomplete dropdown should contain 'gold'"
        );
    });

    QUnit.test("Many2ManyTagsField in a new record", async function (assert) {
        assert.expect(7);

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            mockRPC: (route, { args }) => {
                if (route === "/web/dataset/call_kw/partner/web_save") {
                    const commands = args[1].timmy;
                    assert.strictEqual(commands.length, 1, "should have generated one command");
                    assert.strictEqual(
                        commands[0][0],
                        6,
                        "generated command should be REPLACE WITH"
                    );
                    assert.ok(
                        JSON.stringify(commands[0][2]) === JSON.stringify([12]),
                        "new value should be [12]"
                    );
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
            4,
            "autocomplete dropdown should have 4 entries (2 values + 'Search More...' + 'Search and Edit...')"
        );
        await clickOpenedDropdownItem(target, "timmy", "gold");

        assert.containsOnce(target, ".o_field_many2many_tags .badge", "should contain 1 tag");
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_field_many2many_tags .badge")),
            ["gold"],
            "should contain newly added tag 'gold'"
        );

        // save the record (should do the write RPC with the correct commands)
        await clickSave(target);
    });

    QUnit.test("Many2ManyTagsField: update color", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records[0].color = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                </form>`,
            mockRPC: (route, { args, method }) => {
                if (method === "web_save") {
                    assert.step(JSON.stringify(args[1]));
                }
            },
            resId: 1,
        });

        // First checks that default color 0 is rendered as 0 color
        const badgeNode = target.querySelector(".o_tag.badge");
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

    QUnit.test("Many2ManyTagsField with no_edit_color option", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'color_field': 'color', 'no_edit_color': 1}"/>
                </form>`,
            resId: 1,
        });

        // Click to try to open colorpicker
        await click(target.querySelector(".o_tag.badge"));
        assert.containsNone(target, ".o_colorlist");
    });

    QUnit.test("Many2ManyTagsField in editable list", async function (assert) {
        assert.expect(5);

        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            context: { take: "five" },
            arch: `
                <tree editable="bottom">
                    <field name="timmy" widget="many2many_tags"/>
                </tree>`,
            mockRPC: (route, { kwargs, method, model }) => {
                if (method === "web_read" && model === "partner_type") {
                    assert.strictEqual(
                        kwargs.context.take,
                        "five",
                        "The context should be passed to the RPC"
                    );
                }
            },
        });

        const firstRow = target.querySelector(".o_data_row:nth-child(1)");
        const m2mTagsCell = firstRow.querySelector(".o_many2many_tags_cell");

        assert.containsOnce(firstRow, ".o_field_many2many_tags .badge");

        // edit first row
        await click(m2mTagsCell);

        assert.containsOnce(m2mTagsCell, ".o_field_many2many_selection");

        // add a tag
        await selectDropdownItem(firstRow, "timmy", "silver");

        assert.containsN(firstRow, ".o_field_many2many_tags .badge", 2);

        await clickSave(target);

        assert.containsN(firstRow, ".o_field_many2many_tags .badge", 2);
    });

    QUnit.test("Many2ManyTagsField can load more than 40 records", async function (assert) {
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

    QUnit.test("Many2ManyTagsField keeps focus when being edited", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner.onchanges.foo = function (obj) {
            obj.timmy = [[3, 12]];
        };

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="foo"/>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
            resId: 1,
        });

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

    QUnit.test("Many2ManyTagsField: tags title attribute", async function (assert) {
        serverData.models.turtle.records[0].partner_ids = [2];

        await makeView({
            type: "form",
            serverData,
            resModel: "turtle",
            resId: 1,
            arch: `
                <form>
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
        "Many2ManyTagsField: toggle colorpicker with multiple tags",
        async function (assert) {
            serverData.models.partner.records[0].timmy = [12, 14];
            serverData.models.partner_type.records[0].color = 0;

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
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

    QUnit.test("Many2ManyTagsField: toggle colorpicker multiple times", async function (assert) {
        serverData.models.partner.records[0].timmy = [12];
        serverData.models.partner_type.records[0].color = 0;

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'color_field': 'color'}"/>
                </form>`,
            resId: 1,
        });

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

    QUnit.test("Many2ManyTagsField: quick create a new record", async function (assert) {
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
        await clickOpenedDropdownItem(target, "timmy", `Create "new"`);
        assert.containsOnce(target, ".o_field_many2many_tags .badge");

        await clickSave(target);
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags").textContent.trim(),
            "new"
        );
    });

    QUnit.test("select a many2many value by focusing out", async function (assert) {
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

    QUnit.test(
        "input and remove text without selecting any tag or option",
        async function (assert) {
            serverData.models.partner_type.records.push({ id: 13, display_name: "red", color: 8 });

            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            });

            assert.containsNone(target, ".o_field_many2many_tags .badge");
            const input = target.querySelector(".o_field_many2many_tags input");

            // enter some text
            await triggerEvent(input, null, "focus");
            await click(input);
            await editInput(input, null, "go");
            // ensure no selection
            for (const item of [
                ...target.querySelectorAll(
                    ".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item"
                ),
            ]) {
                triggerEvent(item, null, "mouseleave");
            }
            await triggerEvent(input, null, "blur");
            // ensure we're not adding any value
            assert.containsNone(document.body, ".modal");
            assert.containsNone(target, ".o_field_many2many_tags .badge");

            // remove the added text to test behaviour with falsy value
            await triggerEvent(input, null, "focus");
            await click(input);
            await editInput(input, null, "");
            for (const item of [
                ...target.querySelectorAll(
                    ".o-autocomplete--dropdown-menu .o-autocomplete--dropdown-item"
                ),
            ]) {
                triggerEvent(item, null, "mouseleave");
            }
            await triggerEvent(input, null, "blur");
            assert.containsNone(document.body, ".modal");
            assert.containsNone(target, ".o_field_many2many_tags .badge");
        }
    );

    QUnit.test("Many2ManyTagsField in one2many with display_name", async function (assert) {
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
                </form>`,
            resId: 1,
        });

        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            ["second recordaaa"],
            "the tags should be correctly rendered"
        );

        // open the x2m form view
        await click(target.querySelector('.o_field_one2many[name="turtles"] .o_data_cell'));
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".modal .o_data_cell")),
            ["blip", "My little Foo Value"],
            "the list view should be correctly rendered with foo"
        );

        await click(target.querySelector(".modal button.o_form_button_cancel"));
        assert.deepEqual(
            getNodesTextContent(target.querySelectorAll(".o_data_cell")),
            ["second recordaaa"],
            "the tags should still be correctly rendered"
        );
    });

    QUnit.test("many2many read, field context is properly sent", async function (assert) {
        serverData.models.partner.fields.timmy.context = { hello: "world" };
        serverData.models.partner.records[0].timmy = [12];

        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "web_read" && args.model === "partner") {
                    assert.step(`${args.method} ${args.model}`);
                    assert.strictEqual(args.kwargs.specification.timmy.context.hello, "world");
                }

                if (args.method === "web_read" && args.model === "partner_type") {
                    assert.step(`${args.method} ${args.model}`);
                    assert.strictEqual(args.kwargs.context.hello, "world");
                }
            },
        });

        assert.verifySteps(["web_read partner"]);
        await selectDropdownItem(target, "timmy", "silver");
        assert.verifySteps(["web_read partner_type"]);
    });

    QUnit.test("Many2ManyTagsField: select multiple records", async function (assert) {
        serverData.views = {
            "partner_type,false,list": '<tree><field name="display_name"/></tree>',
            "partner_type,false,search": '<search><field name="display_name"/></search>',
        };

        for (var i = 1; i <= 10; i++) {
            serverData.models.partner_type.records.push({
                id: 100 + i,
                display_name: "Partner" + i,
            });
        }

        await makeView({
            type: "form",
            serverData,
            resModel: "partner",
            resId: 1,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags"/>
                </form>`,
        });

        await selectDropdownItem(target, "timmy", "Search More...");

        assert.ok(target.querySelector(".o_dialog"), "should have open the modal");
        // + 1 for the select all
        assert.containsN(
            target,
            ".o_dialog .o_list_renderer .o_list_record_selector input",
            serverData.models.partner_type.records.length + 1,
            "Should have record selector checkboxes to select multiple records"
        );
        //multiple select tag
        await click(
            target.querySelector(".o_dialog .o_list_renderer .o_list_record_selector input")
        );
        await nextTick(); // necessary for the button to be switched to enabled.
        const selectButton = target.querySelector(".o_dialog .o_select_button");
        assert.ok(!selectButton.disabled, "select button should be enabled");

        await click(selectButton);
        assert.containsNone(target, "o_dialog", "should have closed the modal");
        assert.containsN(
            target,
            '[name="timmy"] .badge',
            serverData.models.partner_type.records.length,
            "many2many tag should now contain 12 records"
        );
    });

    QUnit.test(
        "Many2ManyTagsField: select multiple records doesn't show already added tags",
        async function (assert) {
            serverData.models.partner.records[0].timmy = [12];

            serverData.views = {
                "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                "partner_type,false,search": '<search><field name="display_name"/></search>',
            };

            for (var i = 1; i <= 10; i++) {
                serverData.models.partner_type.records.push({
                    id: 100 + i,
                    display_name: "Partner" + i,
                });
            }

            await makeView({
                type: "form",
                serverData,
                resModel: "partner",
                resId: 1,
                arch: `
                    <form>
                        <field name="timmy" widget="many2many_tags"/>
                    </form>`,
            });

            await selectDropdownItem(target, "timmy", "Search More...");

            // -1 for the one that is already on the form & +1 for the select all,
            assert.containsN(
                target,
                ".o_dialog .o_list_renderer .o_list_record_selector input",
                serverData.models.partner_type.records.length - 1 + 1,
                "Should have record selector checkboxes to select multiple records"
            );

            //multiple select tag
            await click(
                target.querySelector(".o_dialog .o_list_renderer .o_list_record_selector input")
            );
            await nextTick(); // necessary for the button to be switched to enabled.
            await click(target.querySelector(".o_dialog .o_select_button"));
            assert.containsN(
                target,
                '[name="timmy"] .badge',
                serverData.models.partner_type.records.length,
                "many2many tag should now contain 12 records"
            );
        }
    );

    QUnit.test(
        "Many2ManyTagsField: save&new in edit mode doesn't close edit window",
        async function (assert) {
            for (var i = 1; i <= 10; i++) {
                serverData.models.partner_type.records.push({
                    id: 100 + i,
                    display_name: "Partner" + i,
                });
            }

            serverData.views = {
                "partner_type,false,list": '<tree><field name="display_name"/></tree>',
                "partner_type,false,search": '<search><field name="display_name"/></search>',
                "partner_type,false,form": '<form><field name="display_name"/></form>',
            };

            const nameSearchProm = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                    <form>
                        <field name="display_name"/>
                        <field name="timmy" widget="many2many_tags"/>
                    </form>`,
                resId: 1,
                async mockRPC(route, args) {
                    if (args.method === "name_search") {
                        nameSearchProm.resolve();
                    }
                },
            });

            await editInput(target, `div[name="timmy"] input`, "Ralts");
            await nameSearchProm;
            await nextTick();
            await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
            await nextTick();
            //await testUtils.fields.many2one.createAndEdit("timmy", "Ralts");
            assert.containsOnce($(target), ".modal .o_form_view", "should have opened the modal");

            // Create multiple records with save & new
            await editInput(target, ".modal input", "Ralts");
            await click($(".modal .btn-primary:nth-child(2)")[0]);
            await nextTick();
            assert.containsOnce($(target), ".modal .o_form_view", "modal should still be open");
            assert.equal($(".modal input:first")[0].value, "", "input should be empty");

            // Create another record and click save & close
            await editInput(target, ".modal input", "Pikachu");

            await click($(".modal .o_form_buttons_edit .btn-primary:first")[0]);
            assert.containsNone($(target), ".modal .o_list_view", "should have closed the modal");
            assert.containsN(
                target,
                '.o_field_many2many_tags[name="timmy"] .badge',
                2,
                "many2many tag should now contain 2 records"
            );
        }
    );

    QUnit.test(
        "Many2ManyTagsField: make tag name input field blank on Save&New",
        async function (assert) {
            assert.expect(4);

            serverData.views = {
                "partner_type,false,form": '<form><field name="name"/></form>',
            };

            let onchangeCalls = 0;
            const nameSearchProm = makeDeferred();
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
                resId: 1,
                mockRPC: function (route, args) {
                    if (args.method === "name_search") {
                        nameSearchProm.resolve();
                    }
                    if (args.method === "onchange") {
                        if (onchangeCalls === 0) {
                            assert.deepEqual(
                                args.kwargs.context,
                                { default_name: "hello", lang: "en", tz: "taht", uid: 7 },
                                "context should have default_name with 'hello' as value"
                            );
                        }
                        if (onchangeCalls === 1) {
                            assert.deepEqual(
                                args.kwargs.context,
                                { lang: "en", tz: "taht", uid: 7 },
                                "context should have default_name with false as value"
                            );
                        }
                        onchangeCalls++;
                    }
                },
            });

            await editInput(target, ".o_field_widget input", "hello");
            await nameSearchProm;
            await nextTick();
            await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
            await nextTick();

            assert.strictEqual(
                target.querySelector(".modal .o_form_view input").value,
                "hello",
                "should contain the 'hello' in the tag name input field"
            );

            // Create record with save & new
            await click(target.querySelector(".modal .btn-primary:nth-child(2)"));
            assert.strictEqual(
                target.querySelector(".modal .o_form_view input").value,
                "",
                "should display the blank value in the tag name input field"
            );
        }
    );

    QUnit.test("Many2ManyTagsField: conditional create/delete actions", async function (assert) {
        serverData.models.turtle.records[0].partner_ids = [2];
        for (var i = 1; i <= 10; i++) {
            serverData.models.partner.records.push({
                id: 100 + i,
                display_name: "Partner" + i,
            });
        }

        serverData.views = {
            "partner,false,list": '<tree><field name="name"/></tree>',
            "partner,false,search": "<search/>",
        };

        let nameSearchProm = makeDeferred();
        await makeView({
            type: "form",
            resModel: "turtle",
            serverData,
            arch: `
                <form>
                    <field name="display_name"/>
                    <field name="turtle_bar"/>
                    <field name="partner_ids" options="{'create': [('turtle_bar', '=', True)], 'delete': [('turtle_bar', '=', True)]}" widget="many2many_tags"/>
                </form>`,
            resId: 1,
            mockRPC(route, args) {
                if (args.method === "name_search") {
                    nameSearchProm.resolve();
                }
            },
        });

        // turtle_bar is true -> create and delete actions are available
        assert.containsOnce(
            target,
            ".o_field_many2many_tags.o_field_widget .badge .o_delete",
            "X icon on badges should not be available"
        );

        await clickDropdown(target, "partner_ids");
        await nameSearchProm;
        await nextTick();

        const $dropdown1 = $(target.querySelector(".o-autocomplete.dropdown"));
        assert.containsOnce(
            $dropdown1,
            "li.o_m2o_start_typing a:contains(Start typing...)",
            "autocomplete should contain Start typing..."
        );

        await clickOpenedDropdownItem(target, "partner_ids", "Search More...");

        assert.containsN(
            target,
            ".modal .modal-footer button",
            3,
            "there should be 3 buttons (Select, Create and Cancel) available in the modal footer"
        );

        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // type something that doesn't exist
        nameSearchProm = makeDeferred();
        const input = target.querySelector(".o_field_many2many_tags input");

        await triggerEvent(input, null, "focus");
        await nextTick();
        input.value = "Something that does not exist";

        await triggerEvent(input, null, "keydown", {
            code: "ArrowDown",
            key: "ArrowDown",
            bubbles: true,
        });
        await nameSearchProm;
        await nextTick();

        assert.containsN(
            $(target.querySelector(".o-autocomplete.dropdown")),
            "li.o_m2o_dropdown_option",
            2,
            "autocomplete should contain Create and Create and Edit... options"
        );

        // set turtle_bar false -> create and delete actions are no longer available
        await click($(target.querySelector('.o_field_widget[name="turtle_bar"] input')).first()[0]);
        await nextTick();

        // remove icon should still be there as it doesn't delete records but rather remove links
        assert.containsOnce(
            target,
            ".o_field_many2many_tags.o_field_widget .badge .o_delete",
            "X icon on badge should still be there even after turtle_bar is not checked"
        );

        nameSearchProm = makeDeferred();
        await clickDropdown(target, "partner_ids");
        await nameSearchProm;
        await nextTick();

        // only Search More option should be available
        assert.containsOnce(
            $(target.querySelector(".o-autocomplete.dropdown")),
            "li.o_m2o_dropdown_option",
            "autocomplete should contain only one option"
        );
        assert.containsOnce(
            $(target.querySelector(".o-autocomplete.dropdown")),
            "li.o_m2o_dropdown_option a:contains(Search More...)",
            "autocomplete option should be Search More"
        );

        await clickOpenedDropdownItem(target, "partner_ids", "Search More...");

        assert.containsN(
            document.body,
            ".modal .modal-footer button",
            2,
            "there should be 2 buttons (Select and Cancel) available in the modal footer"
        );

        await click($(".modal .modal-footer .o_form_button_cancel")[0]);

        // type something that does exist in multiple occurrences
        // LPE: to check with AAB
        nameSearchProm = makeDeferred();

        await triggerEvent(input, null, "focus");
        await nextTick();
        input.value = "Pa";

        await triggerEvent(input, null, "keydown", {
            code: "ArrowUp",
            key: "ArrowUp",
            bubbles: true,
        });
        await nextTick();
        await nameSearchProm;
        await nextTick();

        // only Search More option should be available
        assert.containsOnce(
            $(target.querySelector(".o-autocomplete.dropdown")),
            "li.o_m2o_dropdown_option",
            "autocomplete should contain only one option"
        );
        assert.containsOnce(
            $(target.querySelector(".o-autocomplete.dropdown")),
            "li.o_m2o_dropdown_option a:contains(Search More)",
            "autocomplete option should be Search More"
        );
    });

    QUnit.test("failing many2one quick create in a Many2ManyTagsField", async function (assert) {
        assert.expect(5);

        serverData.views = {
            "partner_type,false,form": `
                <form>
                    <field name="name"/>
                    <field name="color"/>
                </form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags"/></form>',
            mockRPC(route, args) {
                if (args.method === "name_create") {
                    throw makeServerError({ type: "ValidationError" });
                }
                if (args.method === "web_save") {
                    assert.deepEqual(args.args[1], {
                        color: 8,
                        name: "new partner",
                    });
                }
            },
        });

        assert.containsNone(target, ".o_field_many2many_tags .badge");

        // try to quick create a record
        await triggerEvent(target, ".o_field_many2many_tags input", "focus");
        await editInput(target, ".o_field_many2many_tags input", "new partner");
        await clickOpenedDropdownItem(target, "timmy", `Create "new partner"`);

        // as the quick create failed, a dialog should be open to 'slow create' the record
        assert.containsOnce(target, ".modal .o_form_view");
        assert.strictEqual($(".modal .o_field_widget[name=name] input").val(), "new partner");

        await editInput(target, ".modal .o_field_widget[name=color] input", 8);
        await click(target.querySelector(".modal footer .o_form_buttons_edit button"));

        assert.containsOnce(target, ".o_field_many2many_tags .badge");
    });

    QUnit.test("navigation in tags (mode 'readonly')", async function (assert) {
        // keep a single line with 2 badges
        serverData.models.partner.records = serverData.models.partner.records.slice(0, 1);
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="timmy" widget="many2many_tags"/>
                </tree>`,
        });

        target.querySelector("tr.o_data_row input[type=checkbox]").focus();
        assert.strictEqual(
            document.activeElement,
            target.querySelector("tr.o_data_row input[type=checkbox]")
        );

        triggerHotkey("ArrowRight");

        assert.strictEqual(
            document.activeElement,
            target.querySelector("tr.o_data_row td[name=timmy]")
        );
    });

    QUnit.test("navigation in tags (mode 'edit')", async function (assert) {
        // keep a single line with 2 badges
        serverData.models.partner.records = serverData.models.partner.records.slice(0, 1);
        serverData.models.partner.records[0].timmy = [12, 14];

        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `
                <tree editable="bottom">
                    <field name="timmy" widget="many2many_tags"/>
                    <field name="name"/>
                </tree>`,
        });

        const row = target.querySelector("tr.o_data_row");
        const m2mTagsCell = row.querySelector(".o_many2many_tags_cell");

        await click(m2mTagsCell);

        assert.containsN(row, ".o_field_many2many_tags .badge", 2);

        assert.strictEqual(
            document.activeElement,
            row.querySelector("[name=timmy] .o-autocomplete--input")
        );

        // press left to focus the rightmost facet
        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            row.querySelector("[name=timmy] .badge:nth-child(2)")
        );

        // press left to focus the leftmost facet
        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            row.querySelector("[name=timmy] .badge:nth-child(1)")
        );

        // press left to focus the input
        triggerHotkey("ArrowLeft");

        assert.strictEqual(
            document.activeElement,
            row.querySelector("[name=timmy] .o-autocomplete--input")
        );
        // press left to focus the leftmost facet
        triggerHotkey("ArrowRight");

        assert.strictEqual(
            document.activeElement,
            row.querySelector("[name=timmy] .badge:nth-child(1)")
        );
        assert.containsN(row, ".o_field_many2many_tags .badge", 2);
        assert.deepEqual(
            [...row.querySelectorAll(".o_field_many2many_tags .badge")].map((el) => el.innerText),
            ["gold", "silver"]
        );

        triggerHotkey("BackSpace");
        await nextTick();

        assert.containsOnce(row, ".o_field_many2many_tags .badge");
        assert.deepEqual(
            [...row.querySelectorAll(".o_field_many2many_tags .badge")].map((el) => el.innerText),
            ["silver"]
        );
        assert.containsOnce(row, ".o-autocomplete--input");
    });

    QUnit.test("Many2ManyTagsField with placeholder", async function (assert) {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags" placeholder="Placeholder"/></form>',
        });

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='timmy'] input").placeholder,
            "Placeholder"
        );

        await selectDropdownItem(target, "timmy", "gold");

        assert.strictEqual(
            target.querySelector(".o_field_widget[name='timmy'] input").placeholder,
            ""
        );
    });

    QUnit.test("Many2ManyTagsField supports 'create' props to be a Boolean", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags" placeholder="Placeholder" options="{'create': False }"/></form>`,
        });

        await click(target.querySelector(".o_field_many2many_tags input"));
        assert.strictEqual(
            target.querySelector(".o_field_many2many_tags .o-autocomplete--dropdown-menu")
                .textContent,
            "goldsilverSearch More..."
        );
    });

    QUnit.test("save a record with an empty many2many_tags required", async function (assert) {
        assert.expect(3);

        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags" required="1"/></form>',
        });

        patchWithCleanup(form.env.services.notification, {
            add: (message, params) => {
                assert.strictEqual(message.toString(), "<ul><li>pokemon</li></ul>");
                assert.deepEqual(params, { title: "Invalid fields: ", type: "danger" });
            },
        });

        await clickSave(target);
        assert.containsOnce(target, "[name='timmy'].o_field_invalid");
    });

    QUnit.test("set a required many2many_tags and save directly", async function (assert) {
        let def;
        const form = await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: '<form><field name="timmy" widget="many2many_tags" required="1"/></form>',
            async mockRPC(route, args) {
                assert.step(args.method);
                if (args.method === "web_read") {
                    await def;
                }
            },
        });
        patchWithCleanup(form.env.services.notification, {
            add: () => assert.step("notification"),
        });

        assert.verifySteps(["get_views", "onchange"]);

        assert.containsNone(target, ".o_tag");

        def = makeDeferred();
        await clickDropdown(target, "timmy");
        await clickOpenedDropdownItem(target, "timmy", "gold");
        assert.containsNone(target, ".o_tag");

        assert.verifySteps(["name_search", "web_read"]);

        await clickSave(target);
        assert.doesNotHaveClass(target, "[name='timmy']", "o_field_invalid");

        assert.verifySteps([]);

        def.resolve();
        await nextTick();

        assert.verifySteps(["web_save"]);
    });

    QUnit.test("Many2ManyTagsField with option 'no_quick_create' set to true", async (assert) => {
        serverData.views = {
            "partner_type,false,form": `<form><field name="name"/><field name="color"/></form>`,
        };
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'no_quick_create': 1}"/>
                </form>`,
        });

        assert.containsNone(target, ".o_tag");
        await editInput(target, ".o_field_many2many_tags .o-autocomplete--input", "new tag");
        assert.containsOnce(target, ".o-autocomplete.dropdown li.o_m2o_dropdown_option");
        assert.hasClass(
            target.querySelector(".o-autocomplete.dropdown li.o_m2o_dropdown_option"),
            "o_m2o_dropdown_option_create_edit"
        );
        await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
        assert.containsOnce(target, ".modal");
        assert.strictEqual(
            target.querySelector(".modal .o_field_widget[name=name] input").value,
            "new tag"
        );
        await click(target.querySelector(".modal .o_form_button_save"));
        assert.containsOnce(target, ".o_tag");
        assert.strictEqual(target.querySelector(".o_tag").innerText, "new tag");
    });

    QUnit.test(
        "Many2ManyTagsField keep the linked records after discard of the quick create dialog",
        async (assert) => {
            serverData.views = {
                "partner_type,false,form": `<form><field name="name"/><field name="color"/></form>`,
            };
            await makeView({
                type: "form",
                resModel: "partner",
                serverData,
                arch: `
                <form>
                    <field name="timmy" widget="many2many_tags" options="{'no_quick_create': 1}"/>
                </form>`,
            });

            assert.containsNone(target, ".o_tag");
            await editInput(target, ".o_field_many2many_tags .o-autocomplete--input", "new tag");
            await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
            await click(target.querySelector(".modal .o_form_button_save"));
            assert.containsOnce(target, ".o_tag");
            await editInput(target, ".o_field_many2many_tags .o-autocomplete--input", "tago");
            await clickOpenedDropdownItem(target, "timmy", "Create and edit...");
            await clickDiscard(target.querySelector(".modal"));
            assert.containsOnce(target, ".o_tag");
        }
    );

    QUnit.test("Many2ManyTagsField with option 'no_create' set to true", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags" options="{'no_create': 1}"/></form>`,
        });

        await editInput(target, ".o_field_many2many_tags .o-autocomplete--input", "new tag");
        assert.containsNone(target, ".o-autocomplete.dropdown li.o_m2o_dropdown_option");
        assert.containsOnce(target, ".o-autocomplete.dropdown li.o_m2o_no_result");
    });

    QUnit.test("Many2ManyTagsField with attribute 'can_create' set to false", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags" can_create="0"/></form>`,
        });

        await editInput(target, ".o_field_many2many_tags .o-autocomplete--input", "new tag");
        assert.containsNone(target, ".o-autocomplete.dropdown li.o_m2o_dropdown_option");
    });

    QUnit.test("Many2ManyTagsField with arch context in form view", async (assert) => {
        await makeView({
            type: "form",
            resModel: "partner",
            serverData,
            arch: `<form><field name="timmy" widget="many2many_tags" context="{ 'append_coucou': True }"/></form>`,
            async mockRPC(route, args, performRPC) {
                const result = await performRPC(route, args);
                if (args.method === "web_read") {
                    if (args.kwargs.context.append_coucou) {
                        assert.step("read with context given");
                        result[0].display_name += " coucou";
                    }
                }
                if (args.method === "name_search") {
                    if (args.kwargs.context.append_coucou) {
                        assert.step("name search with context given");
                        for (const res of result) {
                            res[1] += " coucou";
                        }
                    }
                }
                return result;
            },
        });

        await selectDropdownItem(target, "timmy", "gold coucou");

        assert.verifySteps(["name search with context given", "read with context given"]);
        assert.strictEqual(target.querySelector(".o_field_tags").innerText, "gold coucou");
    });

    QUnit.test("Many2ManyTagsField with arch context in list view", async (assert) => {
        await makeView({
            type: "list",
            resModel: "partner",
            serverData,
            arch: `<list editable="top"><field name="timmy" widget="many2many_tags" context="{ 'append_coucou': True }"/></list>`,
            async mockRPC(route, args, performRPC) {
                const result = await performRPC(route, args);
                if (args.method === "web_read") {
                    if (args.kwargs.context.append_coucou) {
                        assert.step("read with context given");
                        result[0].display_name += " coucou";
                    }
                }
                if (args.method === "name_search") {
                    if (args.kwargs.context.append_coucou) {
                        assert.step("name search with context given");
                        for (const res of result) {
                            res[1] += " coucou";
                        }
                    }
                }
                return result;
            },
        });

        await click(target.querySelector("[name=timmy]"));
        await selectDropdownItem(target, "timmy", "gold coucou");

        assert.verifySteps(["name search with context given", "read with context given"]);
        assert.strictEqual(target.querySelector(".o_field_tags").innerText, "gold coucou");
    });
});
