import { PropertiesField } from "@web/views/fields/properties/properties_field";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { WebClient } from "@web/webclient/webclient";

import { expect, getFixture, test } from "@odoo/hoot";
import {
    click,
    edit,
    press,
    queryAll,
    queryAllTexts,
    queryAllValues,
    queryAttribute,
    queryFirst,
    waitFor,
} from "@odoo/hoot-dom";
import { animationFrame, mockDate, runAllTimers } from "@odoo/hoot-mock";
import { editTime, getPickerCell } from "@web/../tests/core/datetime/datetime_test_helpers";
import {
    clickCancel,
    clickSave,
    contains,
    defineModels,
    fields,
    getService,
    models,
    mountView,
    mountWithCleanup,
    onRpc,
    patchWithCleanup,
    serverState,
    toggleActionMenu,
    toggleMenuItem,
} from "@web/../tests/web_test_helpers";

async function closePopover() {
    // Close the popover by clicking outside
    await click(getFixture());
    await runAllTimers();
    await animationFrame();
}

async function changeType(propertyType) {
    const TYPES = [
        "char",
        "text",
        "html",
        "boolean",
        "integer",
        "float",
        "monetary",
        "date",
        "datetime",
        "selection",
        "tags",
        "many2one",
        "many2many",
        "separator"
    ];
    const propertyTypeIndex = TYPES.indexOf(propertyType);
    await click(".o_field_property_definition_type input");
    await animationFrame();
    await click(`.o-dropdown--menu .dropdown-item:eq(${propertyTypeIndex})`);
    await animationFrame();
}

// -----------------------------------------
// Separators tests utils
// -----------------------------------------

/**
 * @param {boolean[]} propertySpecs
 */
async function makePropertiesGroupView(propertySpecs) {
    // mock random function to have predictable auto generated properties names
    let counter = 1;
    patchWithCleanup(PropertiesField.prototype, {
        generatePropertyName: (propertyType) => {
            counter++;
            const name = `property_gen_${counter}`;
            return propertyType === "html" ? `${name}_html` : name;
        },
    });

    onRpc("has_access", () => true);

    const { properties } = Partner._records[1];
    const definitions = propertySpecs.map((isSeparator, i) => {
        const property = {
            name: `property_${i + 1}`,
            string: isSeparator ? `Separator ${i + 1}` : `Property ${i + 1}`,
            type: isSeparator ? "separator" : "char",
        };
        properties[property.name] = false;
        return property;
    });

    ResCompany._records[0].definitions = definitions;

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties" columns="2"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });
}

async function toggleSeparator(separatorName, isSeparator) {
    await click(`[property-name="${separatorName}"] > * > .o_field_property_open_popover`);
    await animationFrame();
    await changeType(isSeparator ? "separator" : "char");
    if (isSeparator) {
        // set unfold by default when switching to a separator
        await click(`.o_field_property_definition_fold .o_form_label:eq(0)`);
    }
    await closePopover();
}

function getGroups() {
    const groups = queryAll(".o_field_properties .row:first-child .o_property_group");
    return groups.map((group) => [
        [
            queryFirst(".o_field_property_group_label", { root: group })?.innerText || "",
            group.getAttribute("property-name"),
        ],
        ...queryAll("[property-name]:not(.o_property_folded)", { root: group }).map((property) => [
            property.innerText,
            property.getAttribute("property-name"),
        ]),
    ]);
}

function getPropertyHandleElement(propertyName) {
    return queryFirst(`*[property-name='${propertyName}'] .oi-draggable`);
}

class Partner extends models.Model {
    display_name = fields.Char();
    properties = fields.Properties({
        string: "Properties",
        searchable: false,
        definition_record: "company_id",
        definition_record_field: "definitions",
    });
    company_id = fields.Many2one({
        string: "Company",
        relation: "res.company",
    });
    _records = [
        {
            id: 1,
            display_name: "first partner",
            properties: {
                property_1: "char value",
                property_2: "b",
            },
            company_id: 37,
        },
        {
            id: 2,
            display_name: "second partner",
            properties: {
                property_1: "char value",
                property_2: "c",
                property_3: "char value 3",
                property_4: "char value 4",
            },
            company_id: 37,
        },
        {
            id: 3,
            display_name: "third partner",
            properties: {
                property_1: false,
                property_3: false,
                property_4: false,
            },
            company_id: 37,
        },
        {
            id: 4,
            display_name: "fourth partner",
            properties: {},
            company_id: 37,
        },
    ];
}

class ResCompany extends models.Model {
    _name = "res.company";
    name = fields.Char({ string: "Name" });
    definitions = fields.PropertiesDefinition();
    _records = [
        {
            id: 37,
            name: "Company 1",
            definitions: [
                {
                    name: "property_1",
                    string: "My Char",
                    type: "char",
                    suffix: "suffix",
                    view_in_cards: true,
                },
                {
                    name: "property_2",
                    string: "My Selection",
                    type: "selection",
                    selection: [
                        ["a", "A"],
                        ["b", "B"],
                        ["c", "C"],
                    ],
                    default: "c",
                    view_in_cards: true,
                },
                {
                    name: "property_3",
                    string: "My Char 3",
                    type: "char",
                },
                {
                    name: "property_4",
                    string: "My Char 4",
                    type: "char",
                    view_in_cards: true,
                },
            ],
        },
    ];
}

class User extends models.Model {
    _name = "res.users";

    name = fields.Char({ string: "Name" });

    _records = [
        {
            id: 1,
            name: "Alice",
        },
        {
            id: 2,
            name: "Bob",
        },
        {
            id: 3,
            name: "Eve",
        },
    ];

    has_group() {
        return true;
    }
}

class ResCurrency extends models.Model {
    name = fields.Char();
    symbol = fields.Char();

    _records = Object.entries(serverState.currencies).map(
        ([id, { name, symbol }]) => ({
            id: Number(id) + 1,
            name,
            symbol,
        })
    );
}

defineModels([Partner, ResCompany, User, ResCurrency]);

/**
 * If the current user can not write on the parent, he should not
 * be able to change the properties definition (but he should be able to
 * change the properties value).
 */
test("properties: no access to parent", async () => {
    onRpc("has_access", () => false);

    const formView = await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    patchWithCleanup(formView.env.services.notification, {
        add: (message, options) => {
            expect(message).toBe('Oops! You cannot edit the Company "Company 1".');
        },
    });

    expect(".o_field_properties").toHaveCount(1, { message: "The field must be in the view" });

    await toggleActionMenu();
    expect(".o-dropdown--menu span:contains(Edit Properties)").toHaveCount(1, {
        message: "The 'Edit Properties' btn should be in the cog menu",
    });
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    expect(".o_field_properties:first-child .o_field_property_open_popover").toHaveCount(0, {
        message: "The edit definition button must not be in the view",
    });
    expect(".o_field_properties:first-child .o_property_field_value input:first").toHaveValue(
        "char value"
    );
});

/**
 * If the current user can write on the parent, he should
 * be able to change the properties definition.
 */
test("properties: access to parent", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1, { message: "The field must be in the view" });

    await toggleActionMenu();
    expect(".o-dropdown--menu span:contains(Edit Properties)").toHaveCount(1, {
        message: "Show 'Edit Properties' btn in cog menu",
    });
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    expect(".o_field_properties:first-child .o_field_property_open_popover").not.toBeEmpty({
        message: "The edit definition button must be in the view",
    });

    expect(".o_field_properties:first-child .o_property_field_value input:first").toHaveValue(
        "char value"
    );

    // Open the definition popover
    await click(
        ".o_field_properties:first-child .o_property_field:first-child .o_field_property_open_popover"
    );
    await animationFrame();

    expect(".o_property_field_popover").toHaveCount(1, {
        message: "Should have opened the definition popover",
    });
    expect(".o_field_property_definition_header").toHaveValue("My Char");

    expect(".o_field_property_definition_type input").toHaveValue("Text");

    // Change the property type to "Date & Time"
    await contains(".o_field_property_definition_header").edit("My Datetime");
    await changeType("datetime");
    expect(".o_property_field_popover .o_field_property_definition_type input").toHaveValue(
        "Date & Time",
        { message: "Should have changed the property type" }
    );

    // Choosing a date in the date picker should not close the definition popover
    await click(".o_field_property_definition_value .o_datetime_input");
    await animationFrame();
    await click(getPickerCell("3"));
    await animationFrame();
    expect(".o_datetime_picker").toHaveCount(1);

    expect(".o_property_field_popover").toHaveCount(1, {
        message: "Should not close the definition popover after selecting a date",
    });

    await closePopover();

    // Check that the type change have been propagated
    expect(".o_field_property_label:eq(0)").toHaveText("My Datetime", {
        message: "Should have updated the property label",
    });
    expect(".o_property_field_value .o_datetime_input").toHaveCount(1, {
        message: "Should have changed the property type",
    });

    // Check that the value is reset (because the type changed)
    expect(".o_property_field_value input").toHaveValue("");
    // Discard the form view and check that the properties take its old values
    await clickCancel();
    await animationFrame();
    expect(".o_property_field:first-child .o_property_field_value input:first").toHaveValue(
        "char value",
        { message: "Discarding the form view should reset the old values" }
    );
});

/**
 * Test the creation of a new property.
 */
test("properties: add a new property", async () => {
    ResCompany._records[0].definitions.pop();
    ResCompany._records[0].definitions.pop();

    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    expect(".o-dropdown--menu span:contains(Edit Properties)").toHaveCount(1, {
        message: "The 'Edit Properties' btn should be in the cog menu",
    });
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // Create a new property
    await click(".o_field_property_add button");
    await waitFor(".o_property_field_popover");

    expect(".o_property_field_popover").toHaveCount(1, {
        message: "Should have opened the definition popover",
    });

    expect(".o_field_property_definition_header").toHaveValue("Property 3", {
        message: "Should have added a default label",
    });

    expect(".o_field_property_definition_type input").toHaveValue("Text", {
        message: "Default type must be text",
    });

    await closePopover();

    const properties = queryAll(".o_field_property_label");
    expect(properties).toHaveCount(3);

    const newProperty = properties[2];
    expect(newProperty).toHaveText("Property 3");
});

test.tags("desktop", "focus required");
test("properties: selection", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1);
    expect(".o_property_field:nth-child(2) select").toHaveCount(1);
    expect(".o_property_field:nth-child(2) select").toHaveValue("b");

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    // Edit the selection property
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();

    expect(".o_property_field_popover").toHaveCount(1);

    expect(".o_property_field_popover .o_field_property_selection").toHaveCount(1, {
        message: "Must instantiate the selection component",
    });

    // Check the default option, must be the third one"
    expect(
        ".o_property_field_popover .o_field_property_selection_option:nth-child(1) .fa-star"
    ).toHaveCount(0);
    expect(
        ".o_property_field_popover .o_field_property_selection_option:nth-child(2) .fa-star"
    ).toHaveCount(0);
    expect(
        ".o_property_field_popover .o_field_property_selection_option:nth-child(3) .fa-star"
    ).toHaveCount(1);
    expect(".o_property_field_popover .o_field_property_definition_type input").toHaveValue(
        "Selection"
    );

    const getOptions = () =>
        queryAll(".o_property_field_popover .o_field_property_selection_option");
    const getOptionsValues = () =>
        queryAllValues(".o_property_field_popover .o_field_property_selection_option input");

    // Create a new selection option
    await click(".o_field_property_selection .fa-plus");
    await animationFrame();
    expect(getOptions()).toHaveCount(4, { message: "Should have added the new option" });
    expect(queryFirst("input", { root: getOptions()[3] })).toBeFocused({
        message: "Should focus the new option",
    });
    await edit("New option");
    await runAllTimers();
    // Press enter to add a second new option
    await press("Enter");
    await runAllTimers();
    expect(getOptions()).toHaveCount(5, { message: "Should have added the new option on Enter" });
    expect(queryFirst("input", { root: getOptions()[4] })).toBeFocused({
        message: "Should focus the new option",
    });
    // Up arrow should give the focus to the previous option
    // because the new option is empty and lost focus, it should be removed
    await press("ArrowUp");
    await animationFrame();
    await runAllTimers();
    expect(getOptions()).toHaveCount(4, {
        message: "Should have remove the option because it is empty and lost focus",
    });
    expect(queryFirst("input", { root: getOptions()[3] })).toBeFocused({
        message: "Should focus the previous option",
    });

    // Up again, should focus the previous option
    await press("ArrowUp");
    await animationFrame();
    await runAllTimers();

    expect(getOptions()).toHaveCount(4, { message: "Should not remove any options" });
    expect(queryFirst("input", { root: getOptions()[2] })).toBeFocused();

    // Remove the second option
    await click(".o_field_property_selection_option:nth-child(2) .fa-trash-o");
    await animationFrame();
    expect(getOptionsValues()).toEqual(["A", "C", "New option"], {
        message: "Should have removed the second option",
    });
    await click(".o_field_property_selection_option:nth-child(2) input");
    await animationFrame();
    // test that pressing 'Enter' inserts a new option after the one currently focused (and not last).
    await press("Enter");
    await animationFrame();
    await click(".o_field_property_selection_option:nth-child(3) input");
    await edit("New option 2");
    await runAllTimers();
    await animationFrame();
    expect(getOptionsValues()).toEqual(["A", "C", "New option 2", "New option"], {
        message: "Should have added a new option at the correct spot",
    });

    const getOptionDraggableElement = (index) =>
        queryFirst(
            `.o_field_property_selection_option:nth-child(${
                index + 1
            }) .o_field_property_selection_drag`
        );

    await contains(getOptionDraggableElement(0)).dragAndDrop(getOptionDraggableElement(2));
    expect(getOptionsValues()).toEqual(["C", "New option 2", "A", "New option"]);

    await contains(getOptionDraggableElement(3)).dragAndDrop(getOptionDraggableElement(0));
    expect(getOptionsValues()).toEqual(["New option", "C", "New option 2", "A"]);

    // create an empty option and move it
    await click(".o_field_property_selection > div > .btn-link");
    await animationFrame();
    expect(getOptionsValues()).toEqual(["New option", "C", "New option 2", "A", ""]);
    await contains(getOptionDraggableElement(4)).dragAndDrop(getOptionDraggableElement(1));
    expect(getOptionsValues()).toEqual(["New option", "", "C", "New option 2", "A"]);
});

/**
 * Test the float and the integer property.
 */
test("properties: float and integer", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // change type to float
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await changeType("float");
    await closePopover();

    const editValue = async (newValue, expected, message) => {
        await contains(".o_property_field:nth-child(2) .o_field_property_input").edit(newValue);
        // click away
        await click(".o_form_sheet_bg");
        await animationFrame();
        expect(".o_property_field:nth-child(2) .o_field_property_input").toHaveValue(expected, {
            message,
        });
    };

    await editValue("0", "0.00");
    await editValue("2", "2.00");
    await editValue("2.11", "2.11");
    await editValue("2.1234567", "2.12", "Decimal precision is 2");
    await editValue("azerty", "0.00", "Wrong float value should be interpreted as 0.00");
    await editValue("1,2,3,4,5,6.1,2,3,5", "123,456.12");

    // change type to integer
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await changeType("integer");
    await closePopover();

    await editValue("0", "0");
    await editValue("2", "2");
    await editValue("2.11", "0");
    await editValue("azerty", "0", "Wrong integer value should be interpreted as 0");
    await editValue("1,2,3,4,5,6", "123,456");
    await editValue("1,2,3,4,5,6.1,2,3", "0");
});

/**
 * Test the text property.
 */
test("properties: text", async () => {
    onRpc("has_access", () => true);

    Partner._records = [
        {
            id: 1337,
            company_id: 42,
            properties: {
                property_1: "text value",
            },
        },
    ];

    ResCompany._records.push({
        id: 42,
        name: "Company 2",
        definitions: [
            {
                name: "property_1",
                string: "My Text",
                type: "text",
                view_in_kanban: true,
            },
        ],
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1337,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
    });

    expect(".o_field_properties textarea").toHaveCount(1);
    expect(".o_field_properties textarea").toHaveValue("text value");
});

/**
 * Test the properties re-arrangement
 */
test.tags("desktop");
test("properties: move properties", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1, { message: "The field must be in the view" });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // Edit the selection property
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await waitFor(".o_property_field_popover");
    const popover = queryFirst(".o_property_field_popover");
    expect(popover).toHaveCount(1, { message: "Should have opened the definition popover" });
    // Move the property up
    await contains(queryFirst(".oi-chevron-up", { root: popover })).click();
    expect(queryAllTexts(".o_field_properties .o_field_property_label")).toEqual([
        "My Selection",
        "My Char",
        "My Char 3",
        "My Char 4",
    ]);
    expect(".o_property_field:nth-child(1) .o_property_field_highlight").toHaveCount(1, {
        message: "Should highlight the moved property",
    });

    // Move the property up again, should have no effect
    await click(popover, ".oi-chevron-up");
    expect(queryAllTexts(".o_field_properties .o_field_property_label")).toEqual([
        "My Selection",
        "My Char",
        "My Char 3",
        "My Char 4",
    ]);
    // Move the property down
    await contains(queryFirst(".oi-chevron-down", { root: popover })).click();

    expect(queryAllTexts(".o_field_properties .o_field_property_label")).toEqual([
        "My Char",
        "My Selection",
        "My Char 3",
        "My Char 4",
    ]);

    // Move the property at the bottom
    await contains(queryFirst(".oi-chevron-down", { root: popover })).click();
    await contains(queryFirst(".oi-chevron-down", { root: popover })).click();
    expect(queryAllTexts(".o_field_properties .o_field_property_label")).toEqual([
        "My Char",
        "My Char 3",
        "My Char 4",
        "My Selection",
    ]);

    await closePopover();
    expect(".o_property_field:nth-child(2) .o_property_field_highlight").toHaveCount(0, {
        message: "Should have removed the highlight",
    });
});

/**
 * Test the properties tags
 */
test("properties: tags", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
        actionMenus: {},
    });

    const createNewTag = async (selector, text) => {
        await click(selector);
        await edit(text);
        await runAllTimers();
        await click(".o_field_property_dropdown_add .dropdown-item");
        await animationFrame();
    };

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    // Select the tags type
    await changeType("tags");

    // Create 3 tags
    const tagsInputSelector = ".o_property_field_popover .o_field_property_dropdown_menu input";
    await createNewTag(tagsInputSelector, "A");
    await createNewTag(tagsInputSelector, "B");
    await createNewTag(tagsInputSelector, "C");
    expect(queryAllTexts(".o_tag")).toEqual(["A", "B", "C"]);

    await closePopover();

    // Edit the tags valuegetVisibleTags
    await click(".o_property_field_value .o_input_dropdown input");
    await animationFrame();
    // Check that he newly created tags are available
    const dropdownItemsSelector = ".o_property_field_value .o_input_dropdown .dropdown-item";
    expect(queryAllTexts(dropdownItemsSelector)).toEqual(["A", "B", "C"], {
        message: "Should be able to selected the created tags",
    });

    // Select one tag in the list
    await click(".o_property_field_value .ui-menu-item:nth-child(2)");
    await animationFrame();

    expect(queryAllTexts(".o_property_field_value .o_tag")).toEqual(["B"], {
        message: "Should have selected the tag B",
    });

    // Re-open the tag dropdown and verify that the selected tag is not in the list
    // (because it's already selected)
    await click(".o_property_field_value .o_input_dropdown input");
    await animationFrame();

    expect(queryAllTexts(dropdownItemsSelector)).toEqual(["A", "C"], {
        message: "The tag B is already selected and should not be visible in the dropdown",
    });

    // Create a new tag from the property value component
    await createNewTag(".o_property_field_value .o_field_property_dropdown_menu input", "D");
    expect(queryAllTexts(".o_property_field_value .o_tag")).toEqual(["B", "D"], {
        message: "Should have created and selected the tag D",
    });

    // Re-open the popover and check that the new tag has been added in the definition
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    const popover = queryFirst(".o_property_field_popover");
    expect(queryAllTexts(".o_tag", { root: popover })).toEqual(["A", "B", "C", "D"]);

    // Change the tag color
    await click(".o_tag:nth-child(2)", { root: popover });
    await animationFrame();
    await click(".o_tag_popover .o_colorlist_item_color_11");
    await animationFrame();
    expect(queryFirst(".o_tag:nth-child(2)", { root: popover })).toHaveClass("o_tag_color_11", {
        message: "Should have changed the tag color",
    });

    // Check that the new B color has been propagated in the form view
    await closePopover();
    expect(queryFirst(".o_property_field_value .o_tag:first-child")).toHaveClass("o_tag_color_11", {
        message: "Should have changed the tag color",
    });

    // Open the popover and remove B from the definition
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await click(".o_property_field_popover .o_tag:nth-child(2) .o_delete");
    await closePopover();
    expect(".o_property_field_value .o_tag").toHaveCount(1, {
        message: "Should have unselected the removed tag B",
    });

    // Remove a tag by pressing backspace
    await click(".o_property_field_value .o_input_dropdown input");
    await press("backspace");
    await animationFrame();
    expect(".o_property_field_value .o_tag").toHaveCount(0, {
        message: "Should have unselected the tag",
    });
});

/**
 * Test the properties many2one
 */
test.tags("desktop");
test("properties: many2one", async () => {
    onRpc(({ method, model, args }) => {
        if (method === "has_access") {
            return true;
        } else if (method === "get_available_models" && model === "ir.model") {
            return [
                { model: "res.partner", display_name: "Partner" },
                { model: "res.users", display_name: "User" },
            ];
        } else if (method === "name_search" && model === "res.users") {
            return [
                [1, "Alice"],
                [2, "Bob"],
                [3, "Eve"],
            ];
        } else if (method === "name_create" && model === "res.users") {
            // Add a prefix to check that "name_create"
            // has been called with the right parameters
            return [1234, "Created:" + args[0]];
        } else if (method === "fields_get" && model === "res.users") {
            return {
                name: { searchable: true, string: "Name", type: "char" },
                login: { searchable: true, string: "Name", type: "char" },
            };
        } else if (method === "search_count" && model === "res.users") {
            return 5;
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await waitFor(".o_property_field_popover");
    const popover = queryFirst(".o_property_field_popover");
    // Select the many2one type
    await changeType("many2one");

    // Choose the "User" model
    await click(".o_field_property_definition_model input", { root: popover });
    await animationFrame();
    expect(queryAllTexts(".o_field_property_definition_model .ui-menu-item")).toEqual([
        "Partner",
        "User",
    ]);
    await click(".o_field_property_definition_model .ui-menu-item:nth-child(2)", { root: popover });
    await animationFrame();
    expect(".o_field_property_definition_model input").toHaveValue("User", {
        message: "Should have selected the User model",
    });

    // Choose a many2one value
    await click(".o_field_property_definition_value input", { root: popover });
    await animationFrame();
    await click(".o_field_property_definition_value .ui-menu-item:nth-child(3)", { root: popover });
    await animationFrame();
    expect(".o_field_property_definition_value input").toHaveValue("Eve", {
        message: "Should have selected the third user",
    });

    await closePopover();

    // Quick create a user
    await click(".o_property_field:nth-child(2) .o_property_field_value input");
    await animationFrame();
    await edit("New User");
    await runAllTimers();
    await click(".o_property_field:nth-child(2) .o_m2o_dropdown_option_create .dropdown-item");
    await animationFrame();
    expect(".o_property_field:nth-child(2) .o_property_field_value input").toHaveValue(
        "Created:New User",
        { message: "Should have created a new user" }
    );
});

/**
 * Test the properties many2many
 */
test.tags("desktop");
test("properties: many2many", async () => {
    onRpc(({ method, model, args }) => {
        if (method === "has_access") {
            return true;
        } else if (method === "get_available_models" && model === "ir.model") {
            return [
                { model: "res.partner", display_name: "Partner" },
                { model: "res.users", display_name: "User" },
            ];
        } else if (
            method === "display_name_for" &&
            model === "ir.model" &&
            args[0][0] === "res.users"
        ) {
            return [{ display_name: "User", model: "res.users" }];
        } else if (method === "name_create" && model === "res.users") {
            // Add a prefix to check that "name_create"
            // has been called with the right parameters
            return [1234, "Created:" + args[0]];
        } else if (method === "search_count" && model === "res.users") {
            return 5;
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    const getSelectedUsers = () => queryAllTexts(".o_property_field_value .o_tag_badge_text");

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    const popover = queryFirst(".o_property_field_popover");
    // Select the many2many type
    await changeType("many2many");

    // Choose the "User" model
    await click(".o_field_property_definition_model input", { root: popover });
    await animationFrame();
    expect(queryAllTexts(".o_field_property_definition_model .ui-menu-item")).toEqual([
        "Partner",
        "User",
    ]);

    await click(".o_field_property_definition_model .ui-menu-item:nth-child(2)", { root: popover });
    await animationFrame();
    expect(".o_field_property_definition_model input").toHaveValue("User", {
        message: "Should have selected the User model",
    });

    await closePopover();

    // Add Eve in the list
    await click(".o_property_field:nth-child(2) input");
    await animationFrame();
    await click(".o_property_field:nth-child(2) .ui-menu-item:nth-child(3)");
    await animationFrame();
    expect(getSelectedUsers()).toEqual(["Eve"], { message: "Should have selected the third user" });

    // Add Bob in the list
    await click(".o_property_field:nth-child(2) input");
    await animationFrame();
    await click(".o_property_field:nth-child(2) .ui-menu-item:nth-child(2)");
    await animationFrame();
    expect(getSelectedUsers()).toEqual(["Eve", "Bob"], {
        message: "Should have selected the second user",
    });

    // Quick create a user
    await click(".o_property_field:nth-child(2) .o_property_field_value input");
    await animationFrame();
    await click(".o_property_field:nth-child(2) input");
    await edit("New User");
    await runAllTimers();
    await click(".o_property_field:nth-child(2) .o_m2o_dropdown_option_create");
    await animationFrame();
    expect(getSelectedUsers()).toEqual(["Eve", "Bob", "Created:New User"], {
        message: "Should have created a new user",
    });

    // Remove Bob from the list
    await click(".o_property_field:nth-child(2) .o_tag:nth-child(2) .o_delete");
    await animationFrame();
    expect(getSelectedUsers()).toEqual(["Eve", "Created:New User"], {
        message: "Should have removed Bob from the list",
    });
});

/**
 * When the user creates a property field of type many2many, many2one, etc.
 * and changes the co-model of the field, the model loaded by the "Search more..."
 * modal should correspond to the selected model and should be updated dynamically.
 */
test.tags("desktop");
test("properties: many2one 'Search more...'", async () => {
    onRpc(({ method, model }) => {
        if (["has_access", "has_group"].includes(method)) {
            return true;
        } else if (method === "display_name_for" && model === "ir.model") {
            return [
                { model: "partner", display_name: "Partner" },
                { model: "res.users", display_name: "User" },
            ];
        } else if (method === "get_available_models" && model === "ir.model") {
            return [
                { model: "partner", display_name: "Partner" },
                { model: "res.users", display_name: "User" },
            ];
        }
    });

    // Patch the test data
    Partner._records = [
        {
            id: 1,
            company_id: 37,
            display_name: "Pierre",
            properties: {
                many_2_one: false,
            },
        },
    ];
    ResCompany._records[0].definitions = [
        {
            name: "many_2_one",
            type: "many2one",
            string: "My Many-2-one",
            comodel: "partner",
        },
    ];
    Partner._views[["list", false]] = /* xml */ `
        <list>
            <field name="id"/>
            <field name="display_name"/>
        </list>`;
    User._views[["list", false]] = /* xml */ `
        <list>
            <field name="id"/>
            <field name="display_name"/>
        </list>`;

    // Patch the Many2XAutocomplete default search limit options
    patchWithCleanup(Many2XAutocomplete.defaultProps, {
        searchLimit: 0,
    });

    // Patch the SelectCreateDialog component
    patchWithCleanup(SelectCreateDialog.prototype, {
        /**
         * @override
         */
        setup() {
            super.setup();
            expect.step(this.props.resModel);
        },
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id" invisible="1"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // Opening the popover
    await click('[property-name="many_2_one"] .o_field_property_open_popover');
    await animationFrame();

    const popover = queryFirst(".o_property_field_popover");

    // Opening the "Search more..." modal
    await click(".o_field_property_definition_value input", { root: popover });
    await animationFrame();
    await click(".o_m2o_dropdown_option_search_more", { root: popover });
    await animationFrame();

    // Checking the model loaded
    expect.verifySteps(["partner"]);

    // Closing the modal
    await click(".modal .btn-close");
    await animationFrame();

    // Switching the co-model of the property field
    await click(".o_field_property_definition_model input", { root: popover });
    await animationFrame();
    await click(".o_field_property_definition_model .ui-menu-item:nth-child(2)", { root: popover });
    await animationFrame();

    // Opening the "Search more..." modal
    await click(".o_field_property_definition_value input", { root: popover });
    await animationFrame();
    await click(".o_m2o_dropdown_option_search_more", { root: popover });
    await animationFrame();
    // Checking the model loaded
    expect.verifySteps(["res.users"]);
});

test("properties: date(time) property manipulations", async () => {
    Partner._records.push({
        id: 5000,
        display_name: "third partner",
        properties: {
            property_1: "2019-01-01",
            property_2: "2019-01-01 10:00:00",
        },
        company_id: 37,
    });
    ResCompany._records[0].definitions = [
        {
            name: "property_1",
            string: "My Date",
            type: "date",
        },
        {
            name: "property_2",
            string: "My DateTime",
            type: "datetime",
        },
    ];
    onRpc(({ method, args }) => {
        expect.step(method);
        if (method === "has_access") {
            return true;
        }
        if (method === "web_save") {
            expect(args[1].properties).toEqual([
                {
                    name: "property_1",
                    string: "My Date",
                    type: "date",
                    value: "2018-12-31",
                },
                {
                    name: "property_2",
                    string: "My DateTime",
                    type: "datetime",
                    value: "2018-12-31 11:05:00",
                },
            ]);
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5000,
        arch: /* xml */ `<form><field name="company_id"/><field name="properties"/></form>`,
    });
    expect.verifySteps(["get_views", "web_read"]);

    // check initial properties
    expect("[property-name=property_1] .o_property_field_value input").toHaveValue("01/01/2019");
    expect("[property-name=property_2] .o_property_field_value input").toHaveValue(
        "01/01/2019 11:00:00"
    );

    // edit date property
    await click(".o_property_field[property-name=property_1] input");
    await animationFrame();
    await click(".o_datetime_picker .o_previous");
    await animationFrame();
    await click(getPickerCell("31"));
    expect("[property-name=property_1] input").toHaveValue("12/31/2018");

    // edit date time property
    await click(".o_property_field[property-name=property_2] input");
    await animationFrame();
    await click(".o_datetime_picker .o_previous");
    await animationFrame();
    await click(getPickerCell("31"));
    await animationFrame();
    await editTime("12:05");
    expect("[property-name=property_2] input").toHaveValue("12/31/2018 12:05:00");

    // save
    expect.verifySteps([]);
    await clickSave();
    expect.verifySteps(["web_save"]);
});

/**
 * Changing the type or the model of a property must regenerate it's name.
 * (so if we change the type / model, all other property values on other records
 * are set to False).
 * Resetting the old model / type should reset the original name.
 */
test.tags("desktop");
test("properties: name reset", async () => {
    onRpc(({ method, model }) => {
        if (method === "has_access") {
            return true;
        } else if (method === "get_available_models" && model === "ir.model") {
            return [
                { model: "res.partner", display_name: "Partner" },
                { model: "res.users", display_name: "User" },
            ];
        } else if (method === "display_name_for" && model === "ir.model") {
            return [
                { display_name: "User", model: "res.users" },
                { display_name: "Partner", model: "res.partner" },
            ];
        } else if (method === "search_count") {
            return 5;
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect('.o_property_field[property-name="property_2"]').toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // open the definition popover
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    // change the type to "many2one"
    await changeType("many2one");

    // select the "User" model
    await click(".o_field_property_definition_model input");
    await contains(".o_field_property_definition_model .ui-menu-item:nth-child(2)").click();
    await animationFrame();
    await closePopover();

    // check that the name has been regenerated
    expect(".o_property_field:nth-child(2)").not.toHaveAttribute("property-name", "property_2", {
        message: "Name must have been regenerated",
    });

    // change back to "Selection" and verify that the original name is restored
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await changeType("selection");
    await closePopover();
    await animationFrame();
    expect(".o_property_field:nth-child(2)").toHaveAttribute("property-name", "property_2", {
        message: "Name must have been restored",
    });

    // re-select many2one user
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await changeType("many2one");
    await click(".o_field_property_definition_model input");
    await contains(".o_field_property_definition_model .ui-menu-item:nth-child(2)").click();
    await animationFrame();
    const propertyName = queryAttribute(".o_property_field:nth-child(2)", "property-name");
    expect(propertyName.endsWith("_html")).toEqual(false);

    // save (if we do not save, the name will be the same even if
    // we change the model, because it would be useless to regenerate it again)
    await closePopover();

    // restore the model "User", and check that the name has been restored
    await contains(".o_property_field:nth-child(2) .o_field_property_open_popover").click();
    await contains(".o_field_property_definition_model input").click();
    await contains(".o_field_property_definition_model .ui-menu-item:nth-child(2)").click();
    await closePopover();
    expect(".o_property_field:nth-child(2)").toHaveAttribute("property-name", propertyName);

    // Change the definition and check that the name stay the same
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await contains(".o_field_property_definition_kanban input").click();
    await closePopover();
    expect(".o_property_field:nth-child(2)").toHaveAttribute("property-name", propertyName);

    // Change the type to "HTML" and verify that the suffix is added
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await changeType("html");
    await closePopover();
    await animationFrame();
    const htmlPropertyName = queryAttribute(".o_property_field:nth-child(2)", "property-name");
    expect(htmlPropertyName.endsWith("_html")).toEqual(true);

    // Restore the selection type, the name should be restored
    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();
    await changeType("selection");
    await closePopover();
    await animationFrame();
    expect(".o_property_field:nth-child(2)").toHaveAttribute("property-name", "property_2", {
        message: "Name must have been restored",
    });
});

/**
 * Check the behavior of the properties field in the kanban view.
 */
test("properties: kanban view", async () => {
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="company_id"/> <hr/>
                        <field name="display_name"/> <hr/>
                        <field name="properties" widget="properties"/>
                    </t>
                </templates>
            </kanban>`,
    });

    // check second card
    expect(".o_kanban_record:nth-child(2) .o_card_property_field:nth-child(3)").toHaveText(
        "char value 4"
    );
    expect(".o_kanban_record:nth-child(2) .o_card_property_field:nth-child(1)").toHaveText(
        "char value\nsuffix"
    );
    expect(".o_kanban_record:nth-child(2) .o_card_property_field:nth-child(2)").toHaveText(
        "C"
    );

    // check first card
    expect(".o_kanban_record:nth-child(1) .o_card_property_field").toHaveCount(2);
});

test("properties: kanban view with date and datetime property fields", async () => {
    Partner._records.push({
        id: 40,
        display_name: "fifth partner",
        properties: {
            property_1: "2019-01-01",
            property_2: "2019-01-01 10:00:00",
        },
        company_id: 37,
    });
    ResCompany._records[0].definitions = [
        {
            name: "property_1",
            string: "My Date",
            type: "date",
            value: "2019-01-01",
            view_in_cards: true,
        },
        {
            name: "property_2",
            string: "My DateTime",
            type: "datetime",
            value: "2019-01-01 10:00:00",
            view_in_cards: true,
        },
    ];

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="company_id"/> <hr/>
                        <field name="display_name"/> <hr/>
                        <field name="properties" widget="properties"/>
                    </t>
                </templates>
            </kanban>`,
    });

    // check fifth card
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(1) span").toHaveText(
        "01/01/2019"
    );
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(2) span").toHaveText(
        "01/01/2019 11:00:00"
    );
});

test("properties: kanban view with multiple sources of properties definitions", async () => {
    ResCompany._records.push({
        id: 38,
        name: "Company 2",
        definitions: [
            {
                name: "property_integer",
                string: "My Integer",
                type: "integer",
                view_in_cards: true,
            },
        ],
    });
    Partner._records.push({
        id: 10,
        display_name: "other partner",
        properties: {
            property_integer: 1,
        },
        company_id: 38,
    });

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="company_id"/> <hr/>
                        <field name="display_name"/> <hr/>
                        <field name="properties" widget="properties"/>
                    </t>
                </templates>
            </kanban>`,
    });

    expect(".o_kanban_record:not(.o_kanban_ghost)").toHaveCount(5);
    expect(queryAllTexts(".o_kanban_record:not(.o_kanban_ghost)")).toEqual([
        "Company 1\nfirst partner\nchar value\nsuffix\nB",
        "Company 1\nsecond partner\nchar value\nsuffix\nC\nchar value 4",
        "Company 1\nthird partner",
        "Company 1\nfourth partner",
        "Company 2\nother partner\nMy Integer\n1",
    ]);
});

/**
 * To check label for int, float, boolean, date and datetime fields.
 *  Also check if border class is applied to boolean field or not.
 */
test("properties: kanban view with label and border", async () => {
    Partner._records.push({
        id: 12,
        display_name: "fifth partner",
        properties: {
            property_integer: 12,
            property_float: 12.2,
            property_date: "2023-06-05",
            property_datetime: "2023-06-05 11:05:00",
            property_checkbox: true,
        },
        company_id: 37,
    });
    ResCompany._records[0].definitions.push(
        {
            name: "property_integer",
            string: "My Integer",
            type: "integer",
            view_in_cards: true,
        },
        {
            name: "property_float",
            string: "My Float",
            type: "float",
            view_in_cards: true,
        },
        {
            name: "property_date",
            string: "My Date",
            type: "date",
            view_in_cards: true,
        },
        {
            name: "property_datetime",
            string: "My Datetime",
            type: "datetime",
            view_in_cards: true,
        },
        {
            name: "property_checkbox",
            string: "My Checkbox",
            type: "boolean",
            view_in_cards: true,
        }
    );

    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
                <kanban>
                    <templates>
                        <t t-name="card">
                            <field name="company_id"/> <hr/>
                            <field name="display_name"/> <hr/>
                            <field name="properties" widget="properties"/>
                        </t>
                    </templates>
                </kanban>`,
    });

    // check for label in integer, float, date and datetime field
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(1) label").toHaveText(
        "My Integer"
    );
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(2) label").toHaveText(
        "My Float"
    );
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(3) label").toHaveText(
        "My Date"
    );
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(4) label").toHaveText(
        "My Datetime"
    );

    //check that label and border class is present for checkbox field
    expect(".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(5) .border").toHaveCount(
        1
    );
    expect(
        ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(5) label:eq(0)"
    ).toHaveText("My Checkbox");
});

test("properties: kanban view without properties", async () => {
    Partner._records = [
        {
            id: 40,
            display_name: "first partner",
            properties: false,
            company_id: 37,
        },
    ];
    await mountView({
        type: "kanban",
        resModel: "partner",
        arch: /* xml */ `
            <kanban>
                <templates>
                    <t t-name="card">
                        <field name="company_id"/> <hr/>
                        <field name="display_name"/> <hr/>
                        <field name="properties" widget="properties"/>
                    </t>
                </templates>
            </kanban>`,
    });
    expect(".o_kanban_record:eq(0)").toHaveText("Company 1\nfirst partner");
});

/**
 * Check that the properties are shown when switching view.
 */
test.tags("desktop");
test("properties: switch view on desktop", async () => {
    Partner._views[["kanban", 99]] = /* xml */ `<kanban>
                <templates>
                    <t t-name="card">
                        <field name="company_id"/> <hr/>
                        <field name="display_name"/> <hr/>
                        <field name="properties" widget="properties"/>
                    </t>
                </templates>
            </kanban>`;
    Partner._views[["list", 100]] = /* xml */ `<list limit="1">
                <field name="display_name"/>
                <field name="properties"/>
            </list>`;
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "list"],
        ],
    });
    await animationFrame();
    await click(".o_switch_view.o_list");
    await animationFrame();
    expect(".o_optional_columns_dropdown").toHaveCount(1, {
        message: "Properties should be added as optional columns.",
    });
});

test.tags("mobile");
test("properties: switch view on mobile", async () => {
    Partner._views[["kanban", 99]] = /* xml */ `<kanban>
                <templates>
                    <t t-name="card">
                        <field name="company_id"/> <hr/>
                        <field name="display_name"/> <hr/>
                        <field name="properties" widget="properties"/>
                    </t>
                </templates>
            </kanban>`;
    Partner._views[["list", 100]] = /* xml */ `<list limit="1">
                <field name="display_name"/>
                <field name="properties"/>
            </list>`;
    onRpc("has_group", () => true);
    await mountWithCleanup(WebClient);
    await getService("action").doAction({
        res_model: "partner",
        type: "ir.actions.act_window",
        views: [
            [false, "kanban"],
            [false, "list"],
        ],
    });
    await animationFrame();
    await click(".o_cp_switch_buttons .dropdown-toggle");
    await animationFrame();
    await click(".dropdown-item:contains(List)");
    await animationFrame();
    expect(".o_optional_columns_dropdown").toHaveCount(1, {
        message: "Properties should be added as optional columns.",
    });
});

/**
 * Test the behavior of the default value. It should be propagated on the property
 * value only when we create a new property. If the property already exists, and we
 * change the default value, it should never update the property value.
 */
test("properties: default value", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // add a new property field
    await click(".o_field_property_add button");
    await waitFor(".o_property_field_popover");

    // edit the default value and close the popover definition
    // because we just created the property, the default value should be propagated
    await click(".o_field_property_definition_value input");
    await edit("First Default Value", { confirm: "Enter" });
    await animationFrame();
    await closePopover();

    expect(".o_field_properties .o_property_field:last .o_property_field_value input").toHaveValue(
        "First Default Value"
    );

    // empty the new / existing property value, and re-open the property we created and change the default value
    // it shouldn't be propagated because it's the second time we open the definition
    const checkProperty = async (property) => {
        await click(".o_property_field_value input", { root: property });
        await edit("");
        await runAllTimers();
        await animationFrame();

        await click(".o_field_property_open_popover", { root: property });
        await runAllTimers();
        await animationFrame();

        await click(".o_field_property_definition_value input");
        await edit("Second Default Value");
        await runAllTimers();
        await animationFrame();

        await closePopover();

        expect(queryFirst(".o_property_field_value input", { root: property })).toHaveValue("");
    };
    await checkProperty(".o_field_properties .o_property_field:last");
    const existingProperty = queryFirst(".o_field_properties .o_property_field:nth-child(1)");
    await checkProperty(existingProperty);
});

test("properties: default value date", async () => {
    mockDate("2022-01-03T08:00:00");
    onRpc("has_access", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
        actionMenus: {},
    });
    expect(".o_field_properties").toHaveCount(1, { message: "The field must be in the view" });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // add a new date property
    await click(".o_field_property_add button");
    await waitFor(".o_property_field_popover");
    await changeType("date");
    expect(".o_property_field_popover .o_field_property_definition_type input").toHaveValue(
        "Date",
        { message: "Should have changed the property type" }
    );
    // choose a default value and check that it is propagated on the property field
    await click(".o_field_property_definition_value .o_datetime_input");
    await animationFrame();
    expect(".o_date_picker").toHaveCount(1);
    await click(getPickerCell("3"));
    await animationFrame();
    await closePopover();
    expect(".o_datetime_input").toHaveValue("01/03/2022", {
        message: "The default date value should have been propagated",
    });
    // save the form and check that the default value is not reset
    await click(".o_form_button_save");
    await animationFrame();
    await click(".o_property_field:nth-last-child(2) .o_field_property_open_popover");
    await animationFrame();
    expect(".o_property_field_popover .o_field_property_definition_value input").toHaveValue(
        "01/03/2022"
    );
});

test("properties: suffix", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties");

    await click(".o_field_property_add button");
    await waitFor(".o_property_field_popover");

    await click(".o_field_property_definition_suffix input");
    await edit("kg", { confirm: "Enter" });
    await animationFrame();
    await closePopover();

    expect(".o_field_properties .o_property_field:last .o_property_field_value_suffix").toHaveText(
        "kg"
    );
});

/**
 * check if property field popover closes when clicking on delete property icon.
 */
test("properties: close property popover once clicked on delete icon", async () => {
    onRpc("has_access", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 3,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="display_name"/>
                        <field name="properties" widget="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // We open the property popover
    await click(".o_property_field:first-child .o_field_property_open_popover");
    await animationFrame();
    expect(".o_field_property_definition").toHaveCount(1);

    // Trying to delete the property should have closed its definition popover
    // We click on delete button
    await click(".o_field_property_definition_delete");
    await animationFrame();
    expect(".o_field_property_definition").toHaveCount(0);
});

/**
 * Check the behavior of the domain (properties with "definition_deleted" should be ignored).
 * In that case, some properties start without the flag "definition_deleted".
 */
test("properties: form view and falsy domain, properties are not empty", async () => {
    ResCompany._records[0].definitions.splice(1, 1);

    onRpc("has_access", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 3,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="display_name"/>
                        <field name="properties" widget="properties"/>
                        <div class="o_test_properties_not_empty" invisible="not properties">
                            Properties not empty
                        </div>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    expect(".o_test_properties_not_empty").toHaveCount(1);

    // delete a property, 2 properties left
    await click(".o_property_field:first-child .o_field_property_open_popover");
    await animationFrame();
    await click(".o_field_property_definition_delete");
    await animationFrame();
    await click(".modal-content .btn-primary");
    await animationFrame();
    expect(".o_test_properties_not_empty").toHaveCount(1);

    // delete a property, 1 property left
    await click(".o_property_field:first-child .o_field_property_open_popover");
    await animationFrame();
    await click(".o_field_property_definition_delete");
    await animationFrame();
    await click(".modal-content .btn-primary");
    await animationFrame();
    expect(".o_test_properties_not_empty").toHaveCount(1);

    // delete a property, no property left

    await click(".o_property_field:first-child .o_field_property_open_popover");
    await animationFrame();
    await click(".o_field_property_definition_delete");
    await animationFrame();
    await click(".modal-content .btn-primary");
    await animationFrame();
    expect(".o_test_properties_not_empty").toHaveCount(0);
});

/**
 * Check the behavior of the domain (properties with "definition_deleted" should be ignored).
 * In that case, all properties start with the flag "definition_deleted".
 */
test("properties: form view and falsy domain, properties are empty", async () => {
    ResCompany._records[0].definitions = [];

    onRpc("has_access", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 4,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="display_name"/>
                        <field name="properties" widget="properties"/>
                        <div class="o_test_properties_not_empty" invisible="not properties">
                            Properties not empty
                        </div>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });
    expect(".o_test_properties_not_empty").toHaveCount(0);

    // create the first property
    await toggleActionMenu();
    await click(".o-dropdown--menu span .fa-cogs");
    await animationFrame();
    expect(".o_test_properties_not_empty").toHaveCount(1);
});

test("properties: discard changes", async () => {
    onRpc("has_access", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <field name="company_id"/>
                <field name="properties" widget="properties"/>
            </form>`,
    });
    expect(".o_property_field:first-child input").toHaveValue("char value");
    await contains(".o_property_field:first-child input").edit("char updated");
    expect(".o_property_field:first-child input").toHaveValue("char updated");
    await clickCancel();
    expect(".o_property_field:first-child input").toHaveValue("char value");
});

// ---------------------------------------------------
// Test the properties groups
// ---------------------------------------------------

test.tags("desktop");
test("properties: separators layout", async () => {
    await makePropertiesGroupView([false, false, false, false]);
    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    await toggleSeparator("property_1", true);
    expect(getGroups()).toEqual([
        [
            ["PROPERTY 1", "property_gen_2"],
            ["Property 2", "property_2"],
            ["Property 3", "property_3"],
        ],
        [
            // invisible separator to fill the space
            ["", ""],
            ["Property 4", "property_4"],
        ],
    ]);

    // fold the group
    await click(
        ".o_field_properties .o_property_group[property-name='property_gen_2']:first-child .o_field_property_group_label"
    );
    await animationFrame();
    expect(getGroups()).toEqual([
        [["PROPERTY 1", "property_gen_2"]],
        [
            ["", ""],
            ["Property 4", "property_4"],
        ],
    ]);
    await click(
        ".o_field_properties .o_property_group[property-name='property_gen_2']:first-child .o_field_property_group_label"
    );
    await animationFrame();
    await toggleSeparator("property_3", true);
    expect(getGroups()).toEqual([
        [
            ["PROPERTY 1", "property_gen_2"],
            ["Property 2", "property_2"],
        ],
        [
            ["PROPERTY 3", "property_gen_3"],
            ["Property 4", "property_4"],
        ],
    ]);

    // fold the left group
    await click(".o_property_group[property-name='property_gen_2'] .o_field_property_group_label");
    await animationFrame();
    expect(getGroups()).toEqual([
        [["PROPERTY 1", "property_gen_2"]],
        [
            ["PROPERTY 3", "property_gen_3"],
            ["Property 4", "property_4"],
        ],
    ]);
    await click(".o_property_group[property-name='property_gen_2'] .o_field_property_group_label");
    await animationFrame();
    // create 3 new properties
    await click(".o_field_property_add button");
    await animationFrame();
    await click(".o_field_property_add button");
    await animationFrame();
    await click(".o_field_property_add button");
    await animationFrame();
    await closePopover();
    expect(getGroups()).toEqual([
        [
            ["PROPERTY 1", "property_gen_2"],
            ["Property 2", "property_2"],
        ],
        [
            ["PROPERTY 3", "property_gen_3"],
            ["Property 4", "property_4"],
            ["Property 5", "property_gen_4"],
            ["Property 6", "property_gen_5"],
            ["Property 7", "property_gen_6"],
        ],
    ]);

    // Property 3 is not a separator anymore, should split in columns
    await toggleSeparator("property_gen_3", false);
    expect(getGroups()).toEqual([
        [
            ["PROPERTY 1", "property_gen_2"],
            ["Property 2", "property_2"],
            ["Property 3", "property_3"],
            ["Property 4", "property_4"],
        ],
        [
            // invisible separator to fill the space
            ["", ""],
            ["Property 5", "property_gen_4"],
            ["Property 6", "property_gen_5"],
            ["Property 7", "property_gen_6"],
        ],
    ]);

    // Property 1 is not a separator anymore, there's no separator left,
    // should go back to the original layout
    await toggleSeparator("property_gen_2", false);
    expect(getGroups()).toEqual([
        [
            ["", ""],
            ["Property 1", "property_1"],
            ["Property 2", "property_2"],
            ["Property 3", "property_3"],
            ["Property 4", "property_4"],
        ],
        [
            ["", ""],
            ["Property 5", "property_gen_4"],
            ["Property 6", "property_gen_5"],
            ["Property 7", "property_gen_6"],
        ],
    ]);
});

test("properties: open section by default", async () => {
    onRpc("has_access", () => true);
    ResCompany._records[0].definitions = [
        { name: "property_1", string: "Separator 1", type: "separator", fold_by_default: false },
        { name: "property_2", string: "Property 2", type: "char" },
        { name: "property_3", string: "Separator 3", type: "separator" },
        { name: "property_4", string: "Property 4", type: "char" },
    ];
    delete Partner._records[1].properties.property_1; // remove char value

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 2,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties" columns="2"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });

    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 1", "property_1"],
            ["Property 2", "property_2"],
        ],
        [["SEPARATOR 3", "property_3"]],
    ]);

    await click("div[property-name='property_1'] .o_field_property_group_label");
    await animationFrame();

    expect(getGroups()).toEqual([
        [["SEPARATOR 1", "property_1"]],
        [["SEPARATOR 3", "property_3"]],
    ]);
});

test.tags("desktop");
test("properties: save separator folded state", async () => {
    onRpc("web_save", ({ args }) => {
        expect.step(args[1].properties.map((p) => [p.name, p.value]));
    });

    await makePropertiesGroupView([true, true, true, true]);
    expect(getGroups()).toEqual([
        [["SEPARATOR 1", "property_1"]],
        [["SEPARATOR 2", "property_2"]],
        [["SEPARATOR 3", "property_3"]],
        [["SEPARATOR 4", "property_4"]],
    ]);

    // return true if the given separator is folded
    const foldState = (separatorName) =>
        !queryFirst(`div[property-name='${separatorName}'] .o_field_property_label .fa-caret-down`);

    const assertFolded = (values) => {
        expect(values.length).toBe(4);
        expect(foldState("property_1")).toBe(values[0]);
        expect(foldState("property_2")).toBe(values[1]);
        expect(foldState("property_3")).toBe(values[2]);
        expect(foldState("property_4")).toBe(values[3]);
    };

    await click(
        ".o_field_properties .o_property_group[property-name='property_1'] .o_field_property_group_label"
    );
    await animationFrame();
    assertFolded([true, false, false, false]);

    await click(
        ".o_field_properties .o_property_group[property-name='property_3'] .o_field_property_group_label"
    );
    await animationFrame();
    assertFolded([true, false, true, false]);

    await clickSave();
    expect.verifySteps([[
        ["property_1", true],
        ["property_2", false],
        ["property_3", true],
        ["property_4", false],
    ]]);
});

/**
 * Test the behavior of the properties when we move them inside folded groups
 */
test.tags("desktop");
test("properties: separators move properties", async () => {
    await makePropertiesGroupView([false, true, true, false, true, true, false]);

    // return true if the given separator is folded
    const foldState = (separatorName) =>
        !queryFirst(`div[property-name='${separatorName}'] .o_field_property_label .fa-caret-down`);

    const assertFolded = (values) => {
        expect(values.length).toBe(4);
        expect(foldState("property_2")).toBe(values[0]);
        expect(foldState("property_3")).toBe(values[1]);
        expect(foldState("property_5")).toBe(values[2]);
        expect(foldState("property_6")).toBe(values[3]);
    };

    // fold all groups
    assertFolded([false, false, false, false]);

    await click("div[property-name='property_2'] .o_field_property_group_label");
    await click("div[property-name='property_3'] .o_field_property_group_label");
    await click("div[property-name='property_5'] .o_field_property_group_label");
    await click("div[property-name='property_6'] .o_field_property_group_label");
    await animationFrame();
    assertFolded([true, true, true, true]);

    expect(getGroups()).toEqual([
        [
            ["", ""],
            ["Property 1", "property_1"],
        ],
        [["SEPARATOR 2", "property_2"]],
        [["SEPARATOR 3", "property_3"]],
        [["SEPARATOR 5", "property_5"]],
        [["SEPARATOR 6", "property_6"]],
    ]);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // move the first property down
    await click("[property-name='property_1'] .o_field_property_open_popover");
    await animationFrame();
    await click(".o_field_property_definition .oi-chevron-down");
    await animationFrame();

    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 2", "property_2"],
            ["Property 1", "property_1"],
        ],
        [["SEPARATOR 3", "property_3"]],
        [["SEPARATOR 5", "property_5"]],
        [["SEPARATOR 6", "property_6"]],
    ]);
    assertFolded([false, true, true, true]);

    await click(".o_field_property_definition .oi-chevron-down");
    await animationFrame();
    expect(getGroups()).toEqual([
        [["SEPARATOR 2", "property_2"]],
        [
            ["SEPARATOR 3", "property_3"],
            ["Property 1", "property_1"],
            ["Property 4", "property_4"],
        ],
        [["SEPARATOR 5", "property_5"]],
        [["SEPARATOR 6", "property_6"]],
    ]);
    assertFolded([false, false, true, true]);

    await click(".o_field_property_definition .oi-chevron-down");
    await animationFrame();
    expect(getGroups()).toEqual([
        [["SEPARATOR 2", "property_2"]],
        [
            ["SEPARATOR 3", "property_3"],
            ["Property 4", "property_4"],
            ["Property 1", "property_1"],
        ],
        [["SEPARATOR 5", "property_5"]],
        [["SEPARATOR 6", "property_6"]],
    ]);
    assertFolded([false, false, true, true]);

    await click(".o_field_property_definition .oi-chevron-down");
    await animationFrame();
    expect(getGroups()).toEqual([
        [["SEPARATOR 2", "property_2"]],
        [
            ["SEPARATOR 3", "property_3"],
            ["Property 4", "property_4"],
        ],
        [
            ["SEPARATOR 5", "property_5"],
            ["Property 1", "property_1"],
        ],
        [["SEPARATOR 6", "property_6"]],
    ]);
    assertFolded([false, false, false, true]);

    // fold property 2 and 3
    await closePopover();
    await click("div[property-name='property_2'] .o_field_property_group_label");
    await animationFrame();
    await click("div[property-name='property_3'] .o_field_property_group_label");
    await animationFrame();
    assertFolded([true, true, false, true]);

    // move the property up
    await click("[property-name='property_1'] .o_field_property_open_popover");
    await animationFrame();
    await click(".o_field_property_definition .oi-chevron-up");
    await animationFrame();
    expect(getGroups()).toEqual([
        [["SEPARATOR 2", "property_2"]],
        [
            ["SEPARATOR 3", "property_3"],
            ["Property 4", "property_4"],
            ["Property 1", "property_1"],
        ],
        [["SEPARATOR 5", "property_5"]],
        [["SEPARATOR 6", "property_6"]],
    ]);
    assertFolded([true, false, false, true]);

    await click(".o_field_property_definition .oi-chevron-up");
    await animationFrame();
    await click(".o_field_property_definition .oi-chevron-up");
    await animationFrame();
    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 2", "property_2"],
            ["Property 1", "property_1"],
        ],
        [
            ["SEPARATOR 3", "property_3"],
            ["Property 4", "property_4"],
        ],
        [["SEPARATOR 5", "property_5"]],
        [["SEPARATOR 6", "property_6"]],
    ]);
    assertFolded([false, false, false, true]);

    // now, create a new property, it must unfold the last group
    await click(".o_field_property_add button");
    await animationFrame();
    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 2", "property_2"],
            ["Property 1", "property_1"],
        ],
        [
            ["SEPARATOR 3", "property_3"],
            ["Property 4", "property_4"],
        ],
        [["SEPARATOR 5", "property_5"]],
        [
            ["SEPARATOR 6", "property_6"],
            ["Property 7", "property_7"],
            ["Property 8", "property_gen_2"],
        ],
    ]);
    assertFolded([false, false, false, false]);
});

test.tags("desktop");
test("properties: separators drag and drop", async () => {
    // 2 columns view, 5 properties
    await makePropertiesGroupView([false, false, false, false, false]);
    expect(getGroups()).toEqual([
        [
            ["", ""],
            ["Property 1", "property_1"],
            ["Property 2", "property_2"],
            ["Property 3", "property_3"],
        ],
        [
            ["", ""],
            ["Property 4", "property_4"],
            ["Property 5", "property_5"],
        ],
    ]);

    const getPropertyHandleElement = (propertyName) =>
        queryFirst(`*[property-name='${propertyName}'] .oi-draggable`);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // if we move properties inside the same column, do not generate the group
    await contains(getPropertyHandleElement("property_1")).dragAndDrop(
        getPropertyHandleElement("property_3")
    );
    expect(getGroups()).toEqual([
        [
            ["", ""],
            ["Property 2", "property_2"],
            ["Property 3", "property_3"],
            ["Property 1", "property_1"],
        ],
        [
            ["", ""],
            ["Property 4", "property_4"],
            ["Property 5", "property_5"],
        ],
    ]);

    // but if we move a property in a different column, we need to generate the group
    await contains(getPropertyHandleElement("property_3")).dragAndDrop(
        getPropertyHandleElement("property_4")
    );
    expect(getGroups()).toEqual([
        [
            // should have generated new separator
            // to keep the column separation
            ["GROUP 1", "property_gen_2"],
            ["Property 2", "property_2"],
            ["Property 1", "property_1"],
        ],
        [
            ["GROUP 2", "property_gen_3"],
            ["Property 3", "property_3"],
            ["Property 4", "property_4"],
            ["Property 5", "property_5"],
        ],
    ]);

    // fold the first group
    await click("div[property-name='property_gen_2'] .o_field_property_group_label");

    // drag and drop the firth property in the folded group
    await contains(getPropertyHandleElement("property_5")).dragAndDrop(
        getPropertyHandleElement("property_gen_2")
    );
    // should unfold automatically
    expect(getGroups()).toEqual([
        [
            ["GROUP 1", "property_gen_2"],
            ["Property 2", "property_2"],
            ["Property 1", "property_1"],
            ["Property 5", "property_5"],
        ],
        [
            ["GROUP 2", "property_gen_3"],
            ["Property 3", "property_3"],
            ["Property 4", "property_4"],
        ],
    ]);

    // drag and drop the first group at the second position
    await contains(getPropertyHandleElement("property_gen_2")).dragAndDrop(
        getPropertyHandleElement("property_gen_3")
    );
    expect(getGroups()).toEqual([
        [
            ["GROUP 2", "property_gen_3"],
            ["Property 3", "property_3"],
            ["Property 4", "property_4"],
        ],
        [
            ["GROUP 1", "property_gen_2"],
            ["Property 2", "property_2"],
            ["Property 1", "property_1"],
            ["Property 5", "property_5"],
        ],
    ]);

    // move property 3 at the last position of the other group
    await contains(getPropertyHandleElement("property_3")).dragAndDrop(
        getPropertyHandleElement("property_gen_2")
    );
    expect(getGroups()).toEqual([
        [
            ["GROUP 2", "property_gen_3"],
            ["Property 4", "property_4"],
        ],
        [
            ["GROUP 1", "property_gen_2"],
            ["Property 2", "property_2"],
            ["Property 1", "property_1"],
            ["Property 5", "property_5"],
            ["Property 3", "property_3"],
        ],
    ]);

    // move property 3 at the first position of its group
    await contains(getPropertyHandleElement("property_3")).dragAndDrop(
        getPropertyHandleElement("property_2")
    );
    expect(getGroups()).toEqual([
        [
            ["GROUP 2", "property_gen_3"],
            ["Property 4", "property_4"],
        ],
        [
            ["GROUP 1", "property_gen_2"],
            ["Property 3", "property_3"],
            ["Property 2", "property_2"],
            ["Property 1", "property_1"],
            ["Property 5", "property_5"],
        ],
    ]);
});

test("properties: start in edit mode", async () => {
    onRpc("has_access", () => true);
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties" editMode="True"/>
                    </group>
                </sheet>
            </form>`,
    });
    expect(".o_field_property_add button").toHaveCount(1, {
        message: "The add button must be in the view",
    });
});

test("properties: no add properties action in cogmenu if no properties field", async () => {
    await mountView({
        type: "form",
        resModel: "res.users",
        resId: 1,
        arch: /* xml */ `<form><field name="name"/></form>`,
        actionMenus: {},
    });
    await toggleActionMenu();
    expect(".o-dropdown--menu span:contains(Edit Properties)").toHaveCount(0);
});

test.tags("desktop");
test("properties: onChange return new properties", async () => {
    ResCompany._records.push({
        id: 38,
        name: "Company 2",
        definitions: [
            {
                name: "property_2_1",
                string: "My Char",
                type: "char",
                view_in_kanban: true,
            },
        ],
    });
    Partner._onChanges.company_id = (changes) => {
        if (changes.company_id === 38) {
            changes.properties = [
                {
                    name: "property_2_2",
                    string: "My New Char",
                    type: "char",
                    value: "Hello",
                },
            ];
        }
    };
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
    });

    await click("[name='company_id'] input");
    await edit("Company 2");
    await runAllTimers();
    await click(".dropdown-menu li");
    await animationFrame();
    expect("[name='properties'] .o_property_field").toHaveText("My New Char");
    expect("[name='properties'] .o_property_field input").toHaveValue("Hello");
});

test("new property, change record, change property type", async () => {
    for (const record of Partner._records) {
        record.properties = {};
    }
    ResCompany._records[0].definitions = [];

    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        resIds: [1, 2],
        arch: `
            <form>
                <field name="company_id"/>
                <field name="properties"/>
            </form>`,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    await contains(".o_property_field .o_property_field_value input").edit("aze");
    await contains(".o_pager_next").click();
    expect(".o_property_field .o_property_field_value input").toHaveValue("");
    // Change second record's property type
    await contains(".o_property_field .o_field_property_open_popover").click();
    await changeType("integer");

    await contains(".o_pager_previous").click();
    expect(".o_property_field .o_property_field_value input").toHaveValue("0");
});

test("property many2one, change property type from many2one to integer", async () => {
    Partner._records = [
        {
            id: 1,
            company_id: 37,
            display_name: "Pierre",
            properties: {
                many_2_one: false,
            },
        },
    ];
    ResCompany._records[0].definitions = [
        {
            name: "many_2_one",
            string: "My Many-2-one",
            type: "many2one",
            comodel: "partner",
            domain: false,
        },
    ];

    onRpc(({ method, model, args }) => {
        if (["has_access", "has_group"].includes(method)) {
            return true;
        } else if (method === "display_name_for" && model === "ir.model") {
            return [{ model: "partner", display_name: "Partner" }];
        } else if (method === "get_available_models" && model === "ir.model") {
            return [{ model: "partner", display_name: "Partner" }];
        } else if (method === "web_save") {
            const { name, ...propertiesWithoutName } = args[1].properties[0];
            expect(name).not.toEqual("many_2_one");
            expect(propertiesWithoutName).toEqual({
                string: "My Many-2-one",
                type: "integer",
                value: 0,
                definition_changed: true,
                default: 0,
            });
        }
    });

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        resIds: [1, 2],
        arch: `
            <form>
                <field name="company_id"/>
                <field name="properties"/>
            </form>`,
        actionMenus: {},
    });

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode

    // Change the record's property type
    await contains(".o_property_field .o_field_property_open_popover").click();
    await changeType("integer");

    // save
    await clickSave();
});

test.tags("desktop");
test("properties: moving single property to 2nd group in auto split mode", async () => {
    await makePropertiesGroupView([false]);
    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    const { moveTo, drop } = await contains(getPropertyHandleElement("property_1")).drag();
    const secondGroup = queryFirst(".o_property_group:last-of-type");
    await moveTo(secondGroup, "bottom");
    await drop();
    expect(getGroups()).toEqual([
        [["GROUP 1", "property_gen_2"]],
        [
            ["GROUP 2", "property_gen_3"],
            ["Property 1", "property_1"],
        ],
    ]);
});

test.tags("desktop");
test("properties: moving single property to 1st group", async () => {
    await makePropertiesGroupView([true, true, false]);
    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    await contains(getPropertyHandleElement("property_3")).dragAndDrop(
        getPropertyHandleElement("property_1")
    );
    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 1", "property_1"],
            ["Property 3", "property_3"],
        ],
        [["SEPARATOR 2", "property_2"]],
    ]);
});

test.tags("desktop");
test("properties: split, moving property from 2nd group to 1st", async () => {
    await makePropertiesGroupView([true, false, false]);
    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    await contains(getPropertyHandleElement("property_3")).dragAndDrop(
        getPropertyHandleElement("property_2"),
        "top"
    );
    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 1", "property_1"],
            ["Property 3", "property_3"],
            ["Property 2", "property_2"],
        ],
        [["GROUP 2", "property_gen_2"]],
    ]);
});

test.tags("desktop");
test("properties: split, moving property from 1st group to 2nd", async () => {
    await makePropertiesGroupView([true, false, false, false, false, false]);
    await toggleActionMenu();
    await toggleMenuItem("Edit Properties"); // Start the edition mode
    await contains(getPropertyHandleElement("property_3")).dragAndDrop(
        getPropertyHandleElement("property_6"),
        "top"
    );
    expect(getGroups()).toEqual([
        [
            ["SEPARATOR 1", "property_1"],
            ["Property 2", "property_2"],
            ["Property 4", "property_4"],
        ],
        [
            ["GROUP 2", "property_gen_2"],
            ["Property 5", "property_5"],
            ["Property 3", "property_3"],
            ["Property 6", "property_6"],
        ],
    ]);
});

test("properties: do not write undefined value", async () => {
    Partner._records.push({
        id: 5000,
        display_name: "third partner",
        properties: {
            property_1: "test",
            property_2: undefined,
        },
        company_id: 37,
    });
    ResCompany._records[0].definitions = [
        {
            name: "property_1",
            string: "Property 1",
            type: "char",
        },
        {
            name: "property_2",
            string: "Property 2",
            type: "char",
        },
    ];
    onRpc(({ method, args }) => {
        if (method === "has_access") {
            return true;
        }
        if (method === "web_save") {
            expect.step("web_save");
            expect(args[1].properties).toEqual([
                {
                    name: "property_1",
                    string: "Property 1",
                    type: "char",
                    value: "edited",
                },
                {
                    name: "property_2",
                    string: "Property 2",
                    type: "char",
                    // Value not added here
                },
            ]);
        }
    });
    await mountView({
        type: "form",
        resModel: "partner",
        resId: 5000,
        arch: /* xml */ `<form><field name="company_id"/><field name="properties"/></form>`,
    });

    await contains("[property-name=property_1] input").edit("edited");

    expect.verifySteps([]);
    await clickSave();
    expect.verifySteps(["web_save"]);
});

test("properties: monetary without currency_field", async () => {
    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });
    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties");

    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();

    await click(".o_field_property_definition_type input");
    await animationFrame();
    expect(`.o_field_property_definition_type_menu .o-dropdown-item:contains(Monetary) > div.text-muted`).toHaveAttribute("data-tooltip", "Not possible to create monetary field because there is no currency on current model.");
});

test("properties: monetary with currency_id", async () => {
    Partner._fields.currency_id = fields.Many2one({ relation: "res.currency", default: 1 });

    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="currency_id" invisible="1"/>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });
    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties");

    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();

    await click(".o_field_property_definition_type input");
    await animationFrame();
    expect(`.o_field_property_definition_type_menu .o-dropdown-item:contains(Monetary) > div:not(.text-muted)`).toHaveCount(1);

    await contains(`.o_field_property_definition_type_menu .o-dropdown-item:contains(Monetary)`).click();
    expect(`.o_field_property_definition_currency_field select`).toHaveText("Currency");
    expect(`.o_field_property_definition_currency_field select`).toHaveValue("currency_id");
    expect(".o_field_property_definition_value .o_input > span:eq(0)").toHaveText("$");
    expect(`.o_field_property_definition_value input`).toHaveValue("0.00");

    await closePopover();
    expect(".o_property_field:nth-child(2) .o_property_field_value .o_input > span:eq(0)").toHaveText("$");
    expect(`.o_property_field:nth-child(2) .o_property_field_value input`).toHaveValue("0.00");
});

test("properties: monetary with multiple currency field", async () => {
    Partner._fields.another_currency_id = fields.Many2one({ relation: "res.currency", default: 2 });
    Partner._fields.currency_id = fields.Many2one({ relation: "res.currency", default: 1 });

    onRpc("has_access", () => true);

    await mountView({
        type: "form",
        resModel: "partner",
        resId: 1,
        arch: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="currency_id" invisible="1"/>
                        <field name="another_currency_id" invisible="1"/>
                        <field name="company_id"/>
                        <field name="properties"/>
                    </group>
                </sheet>
            </form>`,
        actionMenus: {},
    });
    expect(".o_field_properties").toHaveCount(1);

    await toggleActionMenu();
    await toggleMenuItem("Edit Properties");

    await click(".o_property_field:nth-child(2) .o_field_property_open_popover");
    await animationFrame();

    await click(".o_field_property_definition_type input");
    await animationFrame();
    expect(`.o_field_property_definition_type_menu .o-dropdown-item:contains(Monetary) > div:not(.text-muted)`).toHaveCount(1);

    await contains(`.o_field_property_definition_type_menu .o-dropdown-item:contains(Monetary)`).click();
    expect(`.o_field_property_definition_currency_field select`).toHaveText("Currency\nAnother currency");
    expect(`.o_field_property_definition_currency_field select`).toHaveValue("currency_id");

    await contains(".o_field_property_definition_currency_field select").select("another_currency_id");
    expect(`.o_field_property_definition_currency_field select`).toHaveValue("another_currency_id");
    expect(".o_field_property_definition_value .o_input > span:eq(1)").toHaveText("€");
    expect(`.o_field_property_definition_value input`).toHaveValue("0.00");

    await closePopover();
    expect(".o_property_field:nth-child(2) .o_property_field_value .o_input > span:eq(1)").toHaveText("€");
    expect(`.o_property_field:nth-child(2) .o_property_field_value input`).toHaveValue("0.00");
});
