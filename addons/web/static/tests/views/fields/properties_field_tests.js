/** @odoo-module **/

import {
    click,
    clickDiscard,
    clickSave,
    dragAndDrop,
    editInput,
    editSelect,
    getFixture,
    nextTick,
    patchWithCleanup,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { toggleActionMenu } from "@web/../tests/search/helpers";
import { createWebClient, doAction } from "@web/../tests/webclient/helpers";
import { Many2XAutocomplete } from "@web/views/fields/relational_utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";
import { SelectCreateDialog } from "@web/views/view_dialogs/select_create_dialog";
import { browser } from "@web/core/browser/browser";
import {
    getPickerApplyButton,
    getPickerCell,
    getTimePickers,
} from "../../core/datetime/datetime_test_helpers";
import { PropertiesField } from "@web/views/fields/properties/properties_field";

let serverData;
let target;

async function closePopover(target) {
    // Close the popover by clicking outside
    document.activeElement.blur();
    await click(document, "html");
}

async function changeType(target, propertyType) {
    const TYPES_INDEX = {
        char: 1,
        integer: 3,
        float: 4,
        datetime: 6,
        selection: 7,
        tags: 8,
        many2one: 9,
        many2many: 10,
        separator: 11,
    };
    const propertyTypeIndex = TYPES_INDEX[propertyType];
    await click(target, ".o_field_property_definition_type input");
    await nextTick();
    await click(
        target,
        `.o_field_property_definition_type .dropdown-item:nth-child(${propertyTypeIndex})`
    );
}

// -----------------------------------------
// Separators tests utils
// -----------------------------------------

async function makePropertiesGroupView(properties) {
    // mock random function to have predictable auto generated properties names
    let counter = 1;
    patchWithCleanup(PropertiesField.prototype, {
        generatePropertyName: () => {
            counter++;
            return `property_gen_${counter}`;
        },
    });

    async function mockRPC(route, { method }) {
        if (["check_access_rights", "check_access_rule"].includes(method)) {
            return true;
        }
    }

    const data = JSON.parse(JSON.stringify(serverData));
    data.models.partner.records[1].properties = properties.map((isSeparator, index) => {
        return {
            name: `property_${index + 1}`,
            string: isSeparator ? `Separator ${index + 1}` : `Property ${index + 1}`,
            type: isSeparator ? "separator" : "char",
        };
    });

    // unfold all separators
    window.localStorage.setItem(
        "properties.fold,company,37",
        JSON.stringify(
            data.models.partner.records[1].properties
                .filter((property) => property.type === "separator")
                .map((property) => property.name)
        )
    );

    // clean other element
    window.localStorage.removeItem("properties.fold,fake.model,1337");

    return await makeView({
        type: "form",
        resModel: "partner",
        resId: 2,
        serverData: data,
        arch: `
            <form>
                <sheet>
                    <group>
                        <field name="company_id"/>
                        <field name="properties" columns="2"/>
                    </group>
                </sheet>
            </form>`,
        mockRPC,
        actionMenus: {},
    });
}

async function toggleSeparator(separatorName, isSeparator) {
    await click(target, `[property-name="${separatorName}"] > * > .o_field_property_open_popover`);
    await changeType(target, isSeparator ? "separator" : "char");
    await closePopover(target);
}

function getGroups() {
    const propertiesField = target.querySelector(".o_field_properties .row");
    const groups = propertiesField.querySelectorAll(".o_property_group");
    return [...groups].map((group) => [
        [
            group.querySelector(".o_field_property_group_label")?.innerText || "",
            group.getAttribute("property-name"),
        ],
        ...[...group.querySelectorAll("[property-name]:not(.o_property_folded)")].map(
            (property) => [property.innerText, property.getAttribute("property-name")]
        ),
    ]);
}

function getLocalStorageFold() {
    return {
        "company,37": JSON.parse(window.localStorage.getItem("properties.fold,company,37")) || [],
        "fake.model,1337":
            JSON.parse(window.localStorage.getItem("properties.fold,fake.model,1337")) || [],
    };
}

QUnit.module("Fields", (hooks) => {
    hooks.beforeEach(() => {
        target = getFixture();
        serverData = {
            models: {
                partner: {
                    fields: {
                        properties: {
                            string: "Properties",
                            type: "properties",
                            searchable: false,
                            definition_record: "company_id",
                            definition_record_field: "definitions",
                        },
                        company_id: {
                            string: "Company",
                            type: "many2one",
                            relation: "company",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "first partner",
                            properties: [
                                {
                                    name: "property_1",
                                    string: "My Char",
                                    type: "char",
                                    value: "char value",
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
                                    value: "b",
                                    default: "c",
                                    view_in_cards: true,
                                },
                            ],
                            company_id: 37,
                        },
                        {
                            id: 2,
                            display_name: "second partner",
                            properties: [
                                {
                                    name: "property_1",
                                    string: "My Char",
                                    type: "char",
                                    value: "char value",
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
                                    value: "c",
                                    default: "c",
                                    view_in_cards: true,
                                },
                                {
                                    name: "property_3",
                                    string: "My Char 3",
                                    type: "char",
                                    value: "char value 3",
                                },
                                {
                                    name: "property_4",
                                    string: "My Char 4",
                                    type: "char",
                                    value: "char value 4",
                                    view_in_cards: true,
                                },
                            ],
                            company_id: 37,
                        },
                        {
                            id: 3,
                            display_name: "third partner",
                            properties: [
                                { name: "property_1", type: "char" },
                                { name: "property_3", type: "char", definition_changed: true },
                                { name: "property_4", type: "char" },
                            ],
                            company_id: 37,
                        },
                        {
                            id: 4,
                            display_name: "fourth partner",
                            properties: [],
                            company_id: 37,
                        },
                    ],
                },
                company: {
                    fields: {
                        name: { string: "Name", type: "char" },
                        definitions: { type: "properties_definitions" },
                    },
                    records: [
                        {
                            id: 37,
                            name: "Company 1",
                            definitions: [
                                {
                                    name: "property_1",
                                    string: "My Char",
                                    type: "char",
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
                    ],
                },
                "res.users": {
                    fields: {
                        name: {
                            string: "Name",
                            type: "char",
                        },
                    },
                    records: [
                        {
                            id: 1,
                            display_name: "Alice",
                        },
                        {
                            id: 2,
                            display_name: "Bob",
                        },
                        {
                            id: 3,
                            display_name: "Eve",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();

        patchWithCleanup(browser, {
            setTimeout: (fn) => fn(),
        });
    });

    QUnit.module("PropertiesField");

    /**
     * If the current user can not write on the parent, he should not
     * be able to change the properties definition (but he should be able to
     * change the properties value).
     */
    QUnit.test("properties: no access to parent", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (method === "check_access_rights") {
                return false;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
            actionMenus: {},
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        await toggleActionMenu(target);
        assert.containsOnce(
            target,
            ".o_cp_action_menus span:contains(Add Properties)",
            "Show Add Properties btn in cog menu",
        );

        const editButton = field.querySelector(".o_field_property_open_popover");
        assert.notOk(editButton, "The edit definition button must not be in the view");

        const property = field.querySelector(".o_property_field_value input");
        assert.strictEqual(property.value, "char value");
    });

    /**
     * If the current user can write on the parent, he should
     * be able to change the properties definition.
     */
    QUnit.test("properties: access to parent", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
            actionMenus: {},
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        await toggleActionMenu(target);
        assert.containsOnce(
            target,
            ".o_cp_action_menus span:contains(Add Properties)",
            "The add button must be in the cog menu",
        );

        const editButton = field.querySelectorAll(".o_field_property_open_popover");
        assert.ok(editButton, "The edit definition button must be in the view");

        const property = field.querySelector(".o_property_field_value input");
        assert.strictEqual(property.value, "char value");

        // Open the definition popover
        await click(target, ".o_property_field:first-child .o_field_property_open_popover");

        const popover = target.querySelector(".o_property_field_popover");
        assert.ok(popover, "Should have opened the definition popover");

        const label = popover.querySelector(".o_field_property_definition_header");
        assert.strictEqual(label.value, "My Char");

        const type = popover.querySelector(".o_field_property_definition_type input");
        assert.strictEqual(type.value, "Text");

        // Change the property type to "Date & Time"
        await editInput(target, ".o_field_property_definition_header", "My Datetime");
        await changeType(target, "datetime");
        assert.strictEqual(type.value, "Date & Time", "Should have changed the property type");

        // Choosing a date in the date picker should not close the definition popover
        await click(target, ".o_field_property_definition_value .o_datetime_input");
        await click(getPickerCell("3").at(0));

        assert.containsOnce(target, ".o_datetime_picker");

        await click(getPickerApplyButton());

        assert.containsOnce(
            target,
            ".o_property_field_popover",
            "Should not close the definition popover after selecting a date"
        );

        await closePopover(target);

        // Check that the type change have been propagated
        const datetimeLabel = field.querySelector(".o_field_property_label");
        assert.strictEqual(
            datetimeLabel.innerText,
            "My Datetime",
            "Should have updated the property label"
        );
        const datetimeComponent = field.querySelector(".o_property_field_value .o_datetime_input");
        assert.ok(datetimeComponent, "Should have changed the property type");

        // Check that the value is reset (because the type changed)
        const inputValue = document.querySelector(".o_property_field_value input");
        assert.notOk(inputValue.value);

        // Discard the form view and check that the properties take its old values
        await clickDiscard(target);
        const propertyValue = document.querySelector(
            ".o_property_field:first-child .o_property_field_value input"
        );
        assert.strictEqual(
            propertyValue.value,
            "char value",
            "Discarding the form view should reset the old values"
        );
    });

    /**
     * Test the creation of a new property.
     */
    QUnit.test("properties: add a new property", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
            actionMenus: {},
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        await toggleActionMenu(target);
        assert.containsOnce(
            target,
            ".o_cp_action_menus span:contains(Add Properties)",
            "The add button must be in the cog menu",
        );

        // Create a new property
        await click(target, ".o_cp_action_menus span .fa-cogs");

        await nextTick();

        const popover = target.querySelector(".o_property_field_popover");
        assert.ok(popover, "Should have opened the definition popover");

        const label = popover.querySelector(".o_field_property_definition_header");
        assert.strictEqual(label.value, "Property 3", "Should have added a default label");

        const type = popover.querySelector(".o_field_property_definition_type input");
        assert.strictEqual(type.value, "Text", "Default type must be text");

        await closePopover(target);

        const properties = field.querySelectorAll(".o_field_property_label");
        assert.strictEqual(properties.length, 3);

        const newProperty = properties[2];
        assert.strictEqual(newProperty.innerText, "Property 3");
    });

    /**
     * Test the selection property.
     */
    QUnit.test("properties: selection", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        const selectionValue = target.querySelector(".o_property_field:nth-child(2) select");
        assert.ok(selectionValue);
        assert.strictEqual(selectionValue.value, "b");

        // Edit the selection property
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");

        const popover = target.querySelector(".o_property_field_popover");
        assert.ok(popover, "Should have opened the definition popover");

        const selectionComponent = popover.querySelector(".o_field_property_selection");
        assert.ok(selectionComponent, "Must instantiate the selection component");

        // Check the default option
        const option1 = popover.querySelector(".o_field_property_selection_option:nth-child(1)");
        assert.notOk(option1.querySelector(".fa-star"), "Default option must be the third one");
        const option2 = popover.querySelector(".o_field_property_selection_option:nth-child(2)");
        assert.notOk(option2.querySelector(".fa-star"), "Default option must be the third one");
        const option3 = popover.querySelector(".o_field_property_selection_option:nth-child(3)");
        assert.ok(option3);
        assert.ok(option3.querySelector(".fa-star"), "Default option must be the third one");

        const type = popover.querySelector(".o_field_property_definition_type input");
        assert.strictEqual(type.value, "Selection");

        const getOptions = () => {
            return popover.querySelectorAll(".o_field_property_selection_option");
        };
        const getOptionsValues = () => {
            return [...getOptions()].map((option) => option.querySelector("input").value);
        };

        // Create a new selection option
        await click(target, ".o_field_property_selection .fa-plus");
        let options = getOptions();
        assert.strictEqual(options.length, 4, "Should have added the new option");
        assert.strictEqual(
            document.activeElement,
            options[3].querySelector("input"),
            "Should focus the new option"
        );

        await editInput(
            target,
            ".o_field_property_selection_option:nth-child(4) input",
            "New option"
        );

        // Press enter to add a second new option
        await triggerEvent(
            target,
            ".o_field_property_selection_option:nth-child(4) input",
            "keydown",
            { key: "Enter" }
        );
        await nextTick();

        options = getOptions();
        assert.strictEqual(options.length, 5, "Should have added the new option on Enter");
        assert.strictEqual(
            document.activeElement,
            options[4].querySelector("input"),
            "Should focus the new option"
        );

        // Up arrow should give the focus to the previous option
        // because the new option is empty and lost focus, it should be removed
        await triggerEvent(
            target,
            ".o_field_property_selection_option:nth-child(5) input",
            "keydown",
            { key: "ArrowUp" }
        );

        await nextTick();

        options = getOptions();
        assert.strictEqual(
            document.activeElement,
            options[3].querySelector("input"),
            "Should focus the previous option"
        );
        assert.strictEqual(
            options.length,
            4,
            "Should have remove the option because it is empty and lost focus"
        );

        await nextTick();

        // Up again, should focus the previous option
        await triggerEvent(
            target,
            ".o_field_property_selection_option:nth-child(4) input",
            "keydown",
            { key: "ArrowUp" }
        );
        await nextTick();

        assert.strictEqual(document.activeElement, options[2].querySelector("input"));
        assert.strictEqual(getOptions().length, 4, "Should not remove any options");

        // Remove the second option
        await click(target, ".o_field_property_selection_option:nth-child(2) .fa-trash-o");
        assert.deepEqual(
            getOptionsValues(),
            ["A", "C", "New option"],
            "Should have removed the second option"
        );

        // focus should be in option C
        assert.strictEqual(document.activeElement, getOptions()[1].querySelector("input"));
        // test that pressing 'Enter' inserts a new option after the one currently focused (and not last).
        await triggerEvent(
            target,
            ".o_field_property_selection_option:nth-child(2) input",
            "keydown",
            { key: "Enter" }
        );
        await editInput(
            target,
            ".o_field_property_selection_option:nth-child(3) input",
            "New option 2"
        );
        assert.deepEqual(
            getOptionsValues(),
            ["A", "C", "New option 2", "New option"],
            "Should have added a new option at the correct spot"
        );

        await nextTick();
        const getOptionDraggableElement = (index) => {
            return target.querySelector(
                `.o_field_property_selection_option:nth-child(${index + 1})` +
                    " .o_field_property_selection_drag"
            );
        };

        await dragAndDrop(getOptionDraggableElement(0), getOptionDraggableElement(2));
        assert.deepEqual(getOptionsValues(), ["C", "New option 2", "A", "New option"]);

        await dragAndDrop(getOptionDraggableElement(3), getOptionDraggableElement(0));
        assert.deepEqual(getOptionsValues(), ["New option", "C", "New option 2", "A"]);

        // create an empty option and move it
        await click(target, ".o_field_property_selection > div > .btn-link");
        assert.deepEqual(getOptionsValues(), ["New option", "C", "New option 2", "A", ""]);
        await dragAndDrop(getOptionDraggableElement(4), getOptionDraggableElement(1));
        assert.deepEqual(getOptionsValues(), ["New option", "", "C", "New option 2", "A"]);
    });

    /**
     * Test the float and the integer property.
     */
    QUnit.test("properties: float and integer", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        // change type to float
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await changeType(target, "float");
        await closePopover(target);

        const editValue = async (newValue, expected) => {
            await editInput(
                target,
                ".o_property_field:nth-child(2) .o_field_property_input",
                newValue
            );
            // click away
            await click(target, ".o_form_sheet_bg");
            const input = target.querySelector(
                ".o_property_field:nth-child(2) .o_field_property_input"
            );
            assert.strictEqual(input.value, expected);
        };

        await editValue("0", "0.00");
        await editValue("2", "2.00");
        await editValue("2.11", "2.11");
        await editValue("2.1234567", "2.12", "Decimal precision is 2");
        await editValue("azerty", "0.00", "Wrong float value should be interpreted as 0.00");
        await editValue("1,2,3,4,5,6.1,2,3,5", "123456.12");

        // change type to integer
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await changeType(target, "integer");
        await closePopover(target);

        await editValue("0", "0");
        await editValue("2", "2");
        await editValue("2.11", "0");
        await editValue("azerty", "0", "Wrong integer value should be interpreted as 0");
        await editValue("1,2,3,4,5,6", "123456");
        await editValue("1,2,3,4,5,6.1,2,3", "0");
    });

    /**
     * Test the properties re-arrangement
     */
    QUnit.test("properties: move properties", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        // Return the properties labels
        const getLabels = () => {
            const labels = target.querySelectorAll(".o_field_properties .o_field_property_label");
            return [...labels].map((label) => label.innerText);
        };

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        // Edit the selection property
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");

        const popover = target.querySelector(".o_property_field_popover");
        assert.ok(popover, "Should have opened the definition popover");

        // Move the property up
        await click(popover, ".oi-chevron-up");
        assert.deepEqual(
            getLabels(),
            ["My Selection", "My Char", "My Char 3", "My Char 4"],
            "Should have moved up the property"
        );
        const movedProperty = target.querySelector(
            ".o_property_field:nth-child(1) .o_property_field_highlight"
        );
        assert.ok(movedProperty, "Should highlight the moved property");

        // Move the property up again, should have no effect
        await click(popover, ".oi-chevron-up");
        assert.deepEqual(getLabels(), ["My Selection", "My Char", "My Char 3", "My Char 4"]);

        // Move the property down
        await click(popover, ".oi-chevron-down");
        assert.deepEqual(getLabels(), ["My Char", "My Selection", "My Char 3", "My Char 4"]);

        // Move the property at the bottom
        await click(popover, ".oi-chevron-down");
        await click(popover, ".oi-chevron-down");
        assert.deepEqual(getLabels(), ["My Char", "My Char 3", "My Char 4", "My Selection"]);

        await closePopover(target);

        const highlightProperty = target.querySelector(
            ".o_property_field:nth-child(2) .o_property_field_highlight"
        );
        assert.notOk(highlightProperty, "Should have removed the highlight");
    });

    /**
     * Test the properties tags
     */
    QUnit.test("properties: tags", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        const createNewTag = async (selector, text) => {
            await click(target, selector);
            await editInput(target, selector, text);
            await triggerEvent(target, selector, "keydown", { key: "Enter" });
            await nextTick();
        };

        const getVisibleTags = (target, selector) => {
            const tags = target.querySelectorAll(selector);
            return [...tags].map((tag) => tag.innerText);
        };

        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        let popover = target.querySelector(".o_property_field_popover");
        // Select the tags type
        await changeType(target, "tags");

        // Create 3 tags
        const tagsInputSelector = ".o_property_field_popover .o_field_property_dropdown_menu input";
        await createNewTag(tagsInputSelector, "A");
        await createNewTag(tagsInputSelector, "B");
        await createNewTag(tagsInputSelector, "C");
        assert.deepEqual(getVisibleTags(popover, ".o_tag"), ["A", "B", "C"]);

        await closePopover(target);

        // Edit the tags value
        const tagsComponent = target.querySelector(".o_property_field_value .o_input_dropdown");
        await click(target, ".o_property_field_value .o_input_dropdown input");

        // Check that he newly created tags are available
        assert.deepEqual(
            getVisibleTags(tagsComponent, ".dropdown-item"),
            ["A", "B", "C"],
            "Should be able to selected the created tags"
        );

        // Select one tag in the list
        await click(target, ".o_property_field_value .ui-menu-item:nth-child(2)");
        assert.deepEqual(
            getVisibleTags(target, ".o_property_field_value .o_tag"),
            ["B"],
            "Should have selected the tag B"
        );

        // Re-open the tag dropdown and verify that the selected tag is not in the list
        // (because it's already selected)
        await click(target, ".o_property_field_value .o_input_dropdown input");
        assert.deepEqual(
            getVisibleTags(tagsComponent, ".dropdown-item"),
            ["A", "C"],
            "The tag B is already selected and should not be visible in the dropdown"
        );

        // Create a new tag from the property value component
        await createNewTag(".o_property_field_value .o_field_property_dropdown_menu input", "D");
        assert.deepEqual(
            getVisibleTags(target, ".o_property_field_value .o_tag"),
            ["B", "D"],
            "Should have created and selected the tag D"
        );

        // Re-open the popover and check that the new tag has been added in the definition
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await nextTick();
        popover = target.querySelector(".o_property_field_popover");
        assert.deepEqual(getVisibleTags(popover, ".o_tag"), ["A", "B", "C", "D"]);

        // Change the tag color
        await click(popover, ".o_tag:nth-child(2)");
        await click(target, ".o_tag_popover .o_colorlist_item_color_11");
        let secondTag = popover.querySelector(".o_tag:nth-child(2)");
        assert.ok(
            secondTag.classList.contains("o_tag_color_11"),
            "Should have changed the tag color"
        );

        // Check that the new B color has been propagated in the form view
        await closePopover(target);
        secondTag = target.querySelector(".o_property_field_value .o_tag:first-child");
        assert.ok(
            secondTag.classList.contains("o_tag_color_11"),
            "Should have changed the tag color"
        );

        // Open the popover and remove B from the definition
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await click(target, ".o_property_field_popover .o_tag:nth-child(2) .o_delete");
        await closePopover();
        const tags = target.querySelectorAll(".o_property_field_value .o_tag");
        assert.strictEqual(tags.length, 1, "Should have unselected the removed tag B");
    });

    /**
     * Test the properties many2one
     */
    QUnit.test("properties: many2one", async function (assert) {
        async function mockRPC(route, { method, model, args, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
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
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        const popover = target.querySelector(".o_property_field_popover");
        // Select the many2one type
        await changeType(target, "many2one");

        // Choose the "User" model
        await click(popover, ".o_field_property_definition_model input");
        let models = target.querySelectorAll(".o_field_property_definition_model .ui-menu-item");
        models = [...models].map((model) => model.innerText);
        assert.deepEqual(models, ["Partner", "User"]);
        await click(popover, ".o_field_property_definition_model .ui-menu-item:nth-child(2)");

        const selectedModel = target.querySelector(".o_field_property_definition_model input");
        assert.strictEqual(selectedModel.value, "User", "Should have selected the User model");

        // Choose a many2one value
        await click(popover, ".o_field_property_definition_value input");
        await click(popover, ".o_field_property_definition_value .ui-menu-item:nth-child(3)");
        let selectedUser = target.querySelector(".o_field_property_definition_value input");
        assert.strictEqual(selectedUser.value, "Eve", "Should have selected the third user");

        await closePopover(target);

        // Quick create a user
        await click(target, ".o_property_field:nth-child(2) .o_property_field_value input");
        await editInput(target, ".o_property_field:nth-child(2) input", "New User");
        await click(target, ".o_property_field:nth-child(2) .o_m2o_dropdown_option_create");
        selectedUser = target.querySelector(
            ".o_property_field:nth-child(2) .o_property_field_value input"
        );
        assert.strictEqual(
            selectedUser.value,
            "Created:New User",
            "Should have created a new user"
        );
    });

    /**
     * Test the properties many2many
     */
    QUnit.test("properties: many2many", async function (assert) {
        async function mockRPC(route, { method, model, args, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
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
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 2,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        const getSelectedUsers = () => {
            const selectedUsers = target.querySelectorAll(
                ".o_property_field_value .o_tag_badge_text"
            );
            return [...selectedUsers].map((badge) => badge.innerText);
        };

        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        const popover = target.querySelector(".o_property_field_popover");
        // Select the many2many type
        await changeType(target, "many2many");

        // Choose the "User" model
        await click(popover, ".o_field_property_definition_model input");
        let models = target.querySelectorAll(".o_field_property_definition_model .ui-menu-item");
        models = [...models].map((model) => model.innerText);
        assert.deepEqual(models, ["Partner", "User"]);
        await click(popover, ".o_field_property_definition_model .ui-menu-item:nth-child(2)");

        const selectedModel = target.querySelector(".o_field_property_definition_model input");
        assert.strictEqual(selectedModel.value, "User", "Should have selected the User model");

        await closePopover(target);

        // Add Eve in the list
        await click(target, ".o_property_field:nth-child(2) input");
        await click(target, ".o_property_field:nth-child(2) .ui-menu-item:nth-child(3)");
        assert.deepEqual(getSelectedUsers(), ["Eve"], "Should have selected the third user");

        // Add Bob in the list
        await click(target, ".o_property_field:nth-child(2) input");
        await click(target, ".o_property_field:nth-child(2) .ui-menu-item:nth-child(2)");
        assert.deepEqual(
            getSelectedUsers(),
            ["Eve", "Bob"],
            "Should have selected the second user"
        );

        // Quick create a user
        await click(target, ".o_property_field:nth-child(2) .o_property_field_value input");
        await editInput(target, ".o_property_field:nth-child(2) input", "New User");
        await click(target, ".o_property_field:nth-child(2) .o_m2o_dropdown_option_create");
        assert.deepEqual(
            getSelectedUsers(),
            ["Eve", "Bob", "Created:New User"],
            "Should have created a new user"
        );

        // Remove Bob from the list
        await click(target, ".o_property_field:nth-child(2) .o_tag:nth-child(2) .o_delete");
        assert.deepEqual(
            getSelectedUsers(),
            ["Eve", "Created:New User"],
            "Should have removed Bob from the list"
        );
    });

    /**
     * When the user creates a property field of type many2many, many2one, etc.
     * and changes the co-model of the field, the model loaded by the "Search more..."
     * modal should correspond to the selected model and should be updated dynamically.
     */
    QUnit.test("properties: many2one 'Search more...'", async function (assert) {
        async function mockRPC(route, { method, model }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
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
        }

        // Patch the test data
        serverData.models.partner.records = [
            {
                id: 1,
                company_id: 37,
                display_name: "Pierre",
                properties: [
                    {
                        name: "many_2_one",
                        type: "many2one",
                        string: "My Many-2-one",
                        comodel: "partner",
                    },
                ],
            },
        ];
        serverData.views = {
            "partner,false,list": `
                <tree>
                    <field name="id"/>
                    <field name="display_name"/>
                </tree>`,
            "res.users,false,list": `
                <tree>
                    <field name="id"/>
                    <field name="display_name"/>
                </tree>`,
            "res.users,false,search": `<search/>`,
        };

        // Patch the Many2XAutocomplete default search limit options
        patchWithCleanup(Many2XAutocomplete.defaultProps, {
            searchLimit: -1,
        });

        // Patch the SelectCreateDialog component
        patchWithCleanup(SelectCreateDialog.prototype, {
            /**
             * @override
             */
            setup() {
                super.setup();
                assert.step(this.props.resModel);
            },
        });

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id" invisible="1"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        // Opening the popover
        await click(target, '[property-name="many_2_one"] .o_field_property_open_popover');
        const popover = target.querySelector(".o_property_field_popover");

        // Opening the "Search more..." modal
        await click(popover, ".o_field_property_definition_value input");
        await click(popover, ".o_m2o_dropdown_option_search_more");

        // Checking the model loaded
        assert.verifySteps(["partner"]);

        // Closing the modal
        await click(target.querySelector(".modal"), ".btn-close");

        // Switching the co-model of the property field
        await click(popover, ".o_field_property_definition_model input");
        await click(popover, ".o_field_property_definition_model .ui-menu-item:nth-child(2)");

        // Opening the "Search more..." modal
        await click(popover, ".o_field_property_definition_value input");
        await click(popover, ".o_m2o_dropdown_option_search_more");

        // Checking the model loaded
        assert.verifySteps(["res.users"]);
    });

    QUnit.test("properties: date(time) property manipulations", async function (assert) {
        serverData.models.partner.records.push({
            id: 5000,
            display_name: "third partner",
            properties: [
                {
                    name: "property_1",
                    string: "My Date",
                    type: "date",
                    value: "2019-01-01",
                },
                {
                    name: "property_2",
                    string: "My DateTime",
                    type: "datetime",
                    value: "2019-01-01 10:00:00",
                },
            ],
            company_id: 37,
        });
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 5000,
            serverData,
            arch: `<form><field name="company_id"/><field name="properties"/></form>`,
            mockRPC(route, { method, args }) {
                assert.step(method);
                if (method === "check_access_rights") {
                    return true;
                }
                if (method === "web_save") {
                    assert.deepEqual(args[1].properties, [
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
            },
        });
        assert.verifySteps(["get_views", "web_read", "check_access_rights"]);

        // check initial properties
        assert.equal(
            target.querySelector("[property-name=property_1] .o_property_field_value input").value,
            "01/01/2019"
        );
        assert.equal(
            target.querySelector("[property-name=property_2] .o_property_field_value input").value,
            "01/01/2019 11:00:00"
        );

        // edit date property
        await click(target, ".o_property_field[property-name=property_1] input");
        await click(getPickerCell("31").at(0));
        assert.equal(target.querySelector("[property-name=property_1] input").value, "12/31/2018");

        // edit date time property
        await click(target, ".o_property_field[property-name=property_2] input");
        await click(getPickerCell("31").at(0));
        const [hourSelect, minuteSelect] = getTimePickers().at(0);
        await editSelect(hourSelect, null, "12");
        await editSelect(minuteSelect, null, "5");
        assert.equal(
            target.querySelector("[property-name=property_2] input").value,
            "12/31/2018 12:05:00"
        );

        // save
        assert.verifySteps([]);
        await clickSave(target);
        assert.verifySteps(["web_save"]);
    });

    /**
     * Changing the type or the model of a property must regenerate it's name.
     * (so if we change the type / model, all other property values on other records
     * are set to False).
     * Resetting the old model / type should reset the original name.
     */
    QUnit.test("properties: name reset", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
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
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        assert.ok(target.querySelector('.o_property_field[property-name="property_2"]'));

        // open the definition popover
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");

        // change the type to "many2one"
        await changeType(target, "many2one");

        // select the "User" model
        await click(target, ".o_field_property_definition_model input");
        await click(target, ".o_field_property_definition_model .ui-menu-item:nth-child(2)");

        await closePopover(target);

        // check that the name has been regenerated
        let property = target.querySelector(".o_property_field:nth-child(2)");
        const propertyName2 = property.getAttribute("property-name");
        assert.ok(propertyName2 !== "property_2", "Name must have been regenerated");

        // change back to "Selection" and verify that the original name is restored
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await changeType(target, "selection");
        await closePopover(target);
        property = target.querySelector(".o_property_field:nth-child(2)");
        const propertyName3 = property.getAttribute("property-name");
        assert.strictEqual(propertyName3, "property_2", "Name must have been restored");

        // re-select many2one user
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await changeType(target, "many2one");
        await click(target, ".o_field_property_definition_model input");
        await click(target, ".o_field_property_definition_model .ui-menu-item:nth-child(2)");
        property = target.querySelector(".o_property_field:nth-child(2)");
        const propertyName4 = property.getAttribute("property-name");

        // save (if we do not save, the name will be the same even if
        // we change the model, because it would be useless to regenerate it again)
        await closePopover(target);

        // restore the model "User", and check that the name has been restored
        await click(target, ".o_property_field:nth-child(2) .o_field_property_open_popover");
        await click(target, ".o_field_property_definition_model input");
        await click(target, ".o_field_property_definition_model .ui-menu-item:nth-child(2)");
        await closePopover(target);
        property = target.querySelector(".o_property_field:nth-child(2)");
        const propertyName6 = property.getAttribute("property-name");
        assert.strictEqual(propertyName4, propertyName6);
    });

    /**
     * Check the behavior of the properties field in the kanban view.
     */
    QUnit.test("properties: kanban view", async function (assert) {
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="company_id"/> <hr/>
                            <field name="display_name"/> <hr/>
                            <field name="properties" widget="properties"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        });

        // check second card
        const property3 = target.querySelector(
            ".o_kanban_record:nth-child(2) .o_card_property_field:nth-child(3) span"
        );
        assert.notEqual(
            property3.innerText,
            "char value 3",
            "The third property should not be visible in the kanban view"
        );
        assert.equal(property3.innerText, "char value 4");
        const property1 = target.querySelector(
            ".o_kanban_record:nth-child(2) .o_card_property_field:nth-child(1) span"
        );
        assert.equal(property1.innerText, "char value");
        const property2 = target.querySelector(
            ".o_kanban_record:nth-child(2) .o_card_property_field:nth-child(2) span"
        );
        assert.equal(property2.innerText, "C");

        // check first card
        const items = target.querySelectorAll(
            ".o_kanban_record:nth-child(1) .o_card_property_field"
        );
        assert.equal(items.length, 2);
    });

    QUnit.test(
        "properties: kanban view with date and datetime property fields",
        async function (assert) {
            serverData.models.partner.records.push({
                id: 40,
                display_name: "fifth partner",
                properties: [
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
                ],
                company_id: 37,
            });

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="company_id"/> <hr/>
                            <field name="display_name"/> <hr/>
                            <field name="properties" widget="properties"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
            });

            // check fifth card
            const property1 = target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(1) span"
            );
            assert.equal(property1.innerText, "01/01/2019");
            const property2 = target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(2) span"
            );
            assert.equal(property2.innerText, "01/01/2019 11:00:00");
        }
    );

    QUnit.test(
        "properties: kanban view with multiple sources of properties definitions",
        async function (assert) {
            const definition = {
                name: "property_integer",
                string: "My Integer",
                type: "integer",
                view_in_cards: true,
            };
            serverData.models.company.records.push({
                id: 38,
                display_name: "Company 2",
                definitions: [definition],
            });
            serverData.models.partner.records.push({
                id: 10,
                display_name: "other partner",
                properties: [
                    {
                        ...definition,
                        value: 1,
                    },
                ],
                company_id: 38,
            });

            await makeView({
                type: "kanban",
                resModel: "partner",
                serverData,
                arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="company_id"/> <hr/>
                                <field name="display_name"/> <hr/>
                                <field name="properties" widget="properties"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
            });

            assert.containsN(target, ".o_kanban_record:not(.o_kanban_ghost)", 5);
            assert.deepEqual(
                [...target.querySelectorAll(".o_kanban_record:not(.o_kanban_ghost)")].map(
                    (el) => el.textContent
                ),
                [
                    "Company 1 first partner char valueB",
                    "Company 1 second partner char valueCchar value 4",
                    "Company 1 third partner ",
                    "Company 1 fourth partner ",
                    "Company 2 other partner My Integer1",
                ]
            );
        }
    );

    /**
     * To check label for int, float, boolean, date and datetime fields.
     *  Also check if border class is applied to boolean field or not.
     */
    QUnit.test("properties: kanban view with label and border", async function (assert) {
        serverData.models.partner.records.push({
            id: 12,
            display_name: "fifth partner",
            properties: [
                {
                    name: "property_integer",
                    string: "My Integer",
                    type: "integer",
                    value: 12,
                    view_in_cards: true,
                },
                {
                    name: "property_float",
                    string: "My Float",
                    type: "float",
                    value: 12.2,
                    view_in_cards: true,
                },
                {
                    name: "property_date",
                    string: "My Date",
                    type: "date",
                    value: "2023-06-05",
                    view_in_cards: true,
                },
                {
                    name: "property_datetime",
                    string: "My Datetime",
                    type: "datetime",
                    value: "2023-06-05 11:05:00",
                    view_in_cards: true,
                },
                {
                    name: "property_checkbox",
                    string: "My Checkbox",
                    type: "boolean",
                    value: true,
                    view_in_cards: true,
                },
            ],
            company_id: 37,
        });

        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
                <kanban>
                    <templates>
                        <t t-name="kanban-box">
                            <div>
                                <field name="company_id"/> <hr/>
                                <field name="display_name"/> <hr/>
                                <field name="properties" widget="properties"/>
                            </div>
                        </t>
                    </templates>
                </kanban>`,
        });

        // check for label in integer, float, date and datetime field
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(1) label"
            ).innerText,
            "My Integer"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(2) label"
            ).innerText,
            "My Float"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(3) label"
            ).innerText,
            "My Date"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(4) label"
            ).innerText,
            "My Datetime"
        );

        //check that label and border class is present for checkbox field
        assert.containsOnce(
            target,
            ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(5) .border"
        );
        assert.strictEqual(
            target.querySelector(
                ".o_kanban_record:nth-child(5) .o_card_property_field:nth-child(5) label"
            ).innerText,
            "My Checkbox"
        );
    });

    QUnit.test("properties: kanban view without properties", async function (assert) {
        serverData.models.partner.records = [
            {
                id: 40,
                display_name: "first partner",
                properties: false,
                company_id: 37,
            },
        ];
        await makeView({
            type: "kanban",
            resModel: "partner",
            serverData,
            arch: `
            <kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="company_id"/> <hr/>
                            <field name="display_name"/> <hr/>
                            <field name="properties" widget="properties"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
        });
        assert.strictEqual(
            target.querySelector(".o_kanban_record").textContent,
            "Company 1 first partner "
        );
    });

    /**
     * Check that the properties are shown when switching view.
     */
    QUnit.test("properties: switch view", async function (assert) {
        serverData.views = {
            "partner,false,search": `<search/>`,
            "partner,99,kanban": `<kanban>
                <templates>
                    <t t-name="kanban-box">
                        <div>
                            <field name="company_id"/> <hr/>
                            <field name="display_name"/> <hr/>
                            <field name="properties" widget="properties"/>
                        </div>
                    </t>
                </templates>
            </kanban>`,
            "partner,100,list": `<list limit="1">
                <field name="display_name"/>
                <field name="properties"/>
            </list>`,
        };
        const wc = await createWebClient({ serverData });
        await doAction(wc, {
            res_model: "partner",
            type: "ir.actions.act_window",
            views: [
                [false, "kanban"],
                [false, "list"],
            ],
        });

        await click(target, ".o_switch_view.o_list");
        assert.ok(
            target.querySelector(".o_optional_columns_dropdown"),
            "Properties should be added as optional columns."
        );
    });

    /**
     * Test the behavior of the default value. It should be propagated on the property
     * value only when we create a new property. If the property already exists, and we
     * change the default value, it should never update the property value.
     */
    QUnit.test("properties: default value", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
            actionMenus: {},
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        // create a new property
        // edit the default value and close the popover definition
        // because we just created the property, the default value should be propagated
        await toggleActionMenu(target);
        await click(target, ".o_cp_action_menus span .fa-cogs");
        await nextTick();
        await editInput(target, ".o_field_property_definition_value input", "First Default Value");
        await closePopover(target);
        const newProperty = field.querySelector(
            ".o_field_properties .o_property_field:nth-child(3)"
        );
        assert.strictEqual(
            newProperty.querySelector(".o_property_field_value input").value,
            "First Default Value"
        );

        // empty the new / existing property value, and re-open the property we created and change the default value
        // it shouldn't be propagated because it's the second time we open the definition
        const existingProperty = field.querySelector(
            ".o_field_properties .o_property_field:nth-child(1)"
        );
        for (const property of [newProperty, existingProperty]) {
            await editInput(property, ".o_property_field_value input", "");
            await click(property, ".o_field_property_open_popover");
            await nextTick();
            await editInput(
                target,
                ".o_field_property_definition_value input",
                "Second Default Value"
            );
            await closePopover(target);
            assert.strictEqual(property.querySelector(".o_property_field_value input").value, "");
        }
    });

    /**
     * check if property field popover closes when clicking on delete property icon.
     */
    QUnit.test(
        "properties: close property popover once clicked on delete icon",
        async function (assert) {
            async function mockRPC(route, { method, model, kwargs }) {
                if (["check_access_rights", "check_access_rule"].includes(method)) {
                    return true;
                }
            }
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 3,
                serverData,
                arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="display_name"/>
                            <field name="properties" widget="properties"/>
                        </group>
                    </sheet>
                </form>`,
                mockRPC,
            });

            // We open the property popover
            await click(target, ".o_property_field:first-child .o_field_property_open_popover");
            assert.containsOnce(target, ".o_field_property_definition");

            // Trying to delete the property should have closed its definition popover
            // We click on delete button
            await click(target, ".o_field_property_definition_delete");
            assert.containsNone(target, ".o_field_property_definition");
        }
    );

    /**
     * Check the behavior of the domain (properies with "definition_deleted" should be ignored).
     * In that case, some properties start without the flag "definition_deleted".
     */
    QUnit.test(
        "properties: form view and falsy domain, properties are not empty",
        async function (assert) {
            async function mockRPC(route, { method, model, kwargs }) {
                if (["check_access_rights", "check_access_rule"].includes(method)) {
                    return true;
                }
            }
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 3,
                serverData,
                arch: `
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
                mockRPC,
            });
            assert.ok(target.querySelector(".o_test_properties_not_empty"));

            // delete a property, 2 properties left
            await click(target, ".o_property_field:first-child .o_field_property_open_popover");
            await click(target, ".o_field_property_definition_delete");
            await click(target, ".modal-content .btn-primary");
            assert.ok(target.querySelector(".o_test_properties_not_empty"));

            // delete a property, 1 property left
            await click(target, ".o_property_field:first-child .o_field_property_open_popover");
            await click(target, ".o_field_property_definition_delete");
            await click(target, ".modal-content .btn-primary");
            assert.ok(target.querySelector(".o_test_properties_not_empty"));

            // delete a property, no property left
            await click(target, ".o_property_field:first-child .o_field_property_open_popover");
            await click(target, ".o_field_property_definition_delete");
            await click(target, ".modal-content .btn-primary");
            assert.notOk(target.querySelector(".o_test_properties_not_empty"));
        }
    );

    /**
     * Check the behavior of the domain (properties with "definition_deleted" should be ignored).
     * In that case, all properties start with the flag "definition_deleted".
     */
    QUnit.test(
        "properties: form view and falsy domain, properties are empty",
        async function (assert) {
            async function mockRPC(route, { method, model, kwargs }) {
                if (["check_access_rights", "check_access_rule"].includes(method)) {
                    return true;
                }
            }
            await makeView({
                type: "form",
                resModel: "partner",
                resId: 4,
                serverData,
                arch: `
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
                mockRPC,
                actionMenus: {},
            });
            assert.notOk(target.querySelector(".o_test_properties_not_empty"));

            // create the first property
            await toggleActionMenu(target);
            await click(target, ".o_cp_action_menus span .fa-cogs");
            assert.ok(target.querySelector(".o_test_properties_not_empty"));
        }
    );

    // ---------------------------------------------------
    // Test the properties groups
    // ---------------------------------------------------

    QUnit.test("properties: separators layout", async function (assert) {
        await makePropertiesGroupView([false, false, false, false]);
        await toggleSeparator("property_1", true);
        assert.deepEqual(getGroups(), [
            [
                ["PROPERTY 1", "property_gen_2"],
                ["Property 2", "property_2"],
                ["Property 3", "property_3"],
            ],
            [
                ["", "property_gen_2"],
                ["Property 4", "property_4"],
            ],
        ]);

        // fold the group
        await click(
            target,
            ".o_field_properties .o_property_group[property-name='property_gen_2']:first-child .o_field_property_group_label"
        );
        assert.deepEqual(getGroups(), [
            [["PROPERTY 1", "property_gen_2"]],
            [["", "property_gen_2"]],
        ]);
        await click(
            target,
            ".o_field_properties .o_property_group[property-name='property_gen_2']:first-child .o_field_property_group_label"
        );

        await toggleSeparator("property_3", true);
        assert.deepEqual(getGroups(), [
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
        await click(
            target,
            ".o_property_group[property-name='property_gen_2'] .o_field_property_group_label"
        );
        assert.deepEqual(getGroups(), [
            [["PROPERTY 1", "property_gen_2"]],
            [
                ["PROPERTY 3", "property_gen_3"],
                ["Property 4", "property_4"],
            ],
        ]);
        await click(
            target,
            ".o_property_group[property-name='property_gen_2'] .o_field_property_group_label"
        );

        // create 3 new properties
        await toggleActionMenu(target);
        await click(target, ".o_cp_action_menus span .fa-cogs");
        await click(target, ".o_field_property_add button");
        await click(target, ".o_field_property_add button");
        await nextTick();
        await closePopover(target);
        assert.deepEqual(getGroups(), [
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
        assert.deepEqual(getGroups(), [
            [
                ["PROPERTY 1", "property_gen_2"],
                ["Property 2", "property_2"],
                ["Property 3", "property_3"],
                ["Property 4", "property_4"],
            ],
            [
                // invisible separator to fill the space
                ["", "property_gen_2"],
                ["Property 5", "property_gen_4"],
                ["Property 6", "property_gen_5"],
                ["Property 7", "property_gen_6"],
            ],
        ]);

        // Property 1 is not a separator anymore, there's no separator left,
        // should go back to the original layout
        await toggleSeparator("property_gen_2", false);
        assert.deepEqual(getGroups(), [
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

    QUnit.test("properties: separators and local storage", async function (assert) {
        await makePropertiesGroupView([false, false, false, false, true, false]);

        // store the fold state of an other properties field to verify that it stay untouched
        // and check that the property that doesn't exist is removed
        window.localStorage.setItem("company,37", JSON.stringify(["fake"]));
        window.localStorage.setItem(
            "properties.fold,fake.model,1337",
            JSON.stringify(["a", "b", "c"])
        );

        assert.deepEqual(getGroups(), [
            [
                ["", ""],
                ["Property 1", "property_1"],
                ["Property 2", "property_2"],
                ["Property 3", "property_3"],
                ["Property 4", "property_4"],
            ],
            [
                ["SEPARATOR 5", "property_5"],
                ["Property 6", "property_6"],
            ],
        ]);

        // fold the group
        await click(target, "div[property-name='property_5'] .o_field_property_group_label");
        assert.deepEqual(getGroups(), [
            [
                ["", ""],
                ["Property 1", "property_1"],
                ["Property 2", "property_2"],
                ["Property 3", "property_3"],
                ["Property 4", "property_4"],
            ],
            [["SEPARATOR 5", "property_5"]],
        ]);
        assert.deepEqual(getLocalStorageFold(), {
            "company,37": [],
            "fake.model,1337": ["a", "b", "c"], // stay untouched
        });

        // unfold the group
        await click(target, "div[property-name='property_5'] .o_field_property_group_label");
        assert.deepEqual(getLocalStorageFold(), {
            "company,37": ["property_5"],
            "fake.model,1337": ["a", "b", "c"], // stay untouched
        });
    });

    /**
     * Test the behavior of the properties when we move them inside folded groups
     */
    QUnit.test("properties: separators move properties", async function (assert) {
        await makePropertiesGroupView([false, true, true, false, true, true, false]);

        // return true if the given separator is folded
        const foldState = (separatorName) => {
            return !target.querySelector(
                `div[property-name='${separatorName}'] .o_field_property_label .fa-caret-down`
            );
        };

        const assertFolded = (values) => {
            assert.strictEqual(values.length, 4);
            assert.strictEqual(values[0], foldState("property_2"));
            assert.strictEqual(values[1], foldState("property_3"));
            assert.strictEqual(values[2], foldState("property_5"));
            assert.strictEqual(values[3], foldState("property_6"));
        };

        // fold all groups
        assertFolded([false, false, false, false]);

        await click(target, "div[property-name='property_2'] .o_field_property_group_label");
        await click(target, "div[property-name='property_3'] .o_field_property_group_label");
        await click(target, "div[property-name='property_5'] .o_field_property_group_label");
        await click(target, "div[property-name='property_6'] .o_field_property_group_label");
        assertFolded([true, true, true, true]);

        assert.deepEqual(getGroups(), [
            [
                ["", ""],
                ["Property 1", "property_1"],
            ],
            [["SEPARATOR 2", "property_2"]],
            [["SEPARATOR 3", "property_3"]],
            [["SEPARATOR 5", "property_5"]],
            [["SEPARATOR 6", "property_6"]],
        ]);

        // move the first property down
        await click(target, "[property-name='property_1'] .o_field_property_open_popover");
        await click(target, ".o_field_property_definition .oi-chevron-down");

        assert.deepEqual(getGroups(), [
            [
                ["SEPARATOR 2", "property_2"],
                ["Property 1", "property_1"],
            ],
            [["SEPARATOR 3", "property_3"]],
            [["SEPARATOR 5", "property_5"]],
            [["SEPARATOR 6", "property_6"]],
        ]);
        assertFolded([false, true, true, true]);

        await click(target, ".o_field_property_definition .oi-chevron-down");
        assert.deepEqual(getGroups(), [
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

        await click(target, ".o_field_property_definition .oi-chevron-down");
        assert.deepEqual(getGroups(), [
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

        await click(target, ".o_field_property_definition .oi-chevron-down");
        assert.deepEqual(getGroups(), [
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
        await closePopover(target);
        await click(target, "div[property-name='property_2'] .o_field_property_group_label");
        await click(target, "div[property-name='property_3'] .o_field_property_group_label");
        assertFolded([true, true, false, true]);

        // move the property up
        await click(target, "[property-name='property_1'] .o_field_property_open_popover");
        await click(target, ".o_field_property_definition .oi-chevron-up");
        assert.deepEqual(getGroups(), [
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

        await click(target, ".o_field_property_definition .oi-chevron-up");
        await click(target, ".o_field_property_definition .oi-chevron-up");
        assert.deepEqual(getGroups(), [
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
        await toggleActionMenu(target);
        await click(target, ".o_cp_action_menus span .fa-cogs");
        assert.deepEqual(getGroups(), [
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

        assert.deepEqual(getLocalStorageFold(), {
            "company,37": ["property_5", "property_3", "property_2", "property_6"],
            "fake.model,1337": [],
        });
    });

    QUnit.test("properties: separators drag and drop", async function (assert) {
        // 2 columns view, 5 properties
        await makePropertiesGroupView([false, false, false, false, false]);
        assert.deepEqual(getGroups(), [
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

        const getPropertyHandleElement = (propertyName) => {
            return target.querySelector(`*[property-name='${propertyName}'] .oi-draggable`);
        };

        // if we move properties inside the same column, do not generate the group
        await dragAndDrop(
            getPropertyHandleElement("property_1"),
            getPropertyHandleElement("property_3")
        );
        assert.deepEqual(getGroups(), [
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
        await dragAndDrop(
            getPropertyHandleElement("property_3"),
            getPropertyHandleElement("property_4")
        );

        assert.deepEqual(getGroups(), [
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
        await click(target, "div[property-name='property_gen_2'] .o_field_property_group_label");

        // drag and drop the firth property in the folded group
        await dragAndDrop(
            getPropertyHandleElement("property_5"),
            getPropertyHandleElement("property_gen_2")
        );

        // should unfold automatically
        assert.deepEqual(getGroups(), [
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
        await dragAndDrop(
            getPropertyHandleElement("property_gen_2"),
            getPropertyHandleElement("property_gen_3")
        );

        assert.deepEqual(getGroups(), [
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
        await dragAndDrop(
            getPropertyHandleElement("property_3"),
            getPropertyHandleElement("property_gen_2")
        );

        assert.deepEqual(getGroups(), [
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
        await dragAndDrop(
            getPropertyHandleElement("property_3"),
            getPropertyHandleElement("property_2")
        );

        assert.deepEqual(getGroups(), [
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

    QUnit.test("properties: showAddButton option", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }
        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties" showAddButton="True"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });
        assert.containsOnce(
            target,
            ".o_field_property_add button",
            "The add button must be in the view",
        );
    });

    QUnit.test(
        "properties: no add properties action in cogmenu if no properties field",
        async function (assert) {
            await makeView({
                type: "form",
                resModel: "res.users",
                resId: 1,
                serverData,
                arch: '<form><field name="name"/></form>',
                actionMenus: {},
            });
            await toggleActionMenu(target);
            assert.containsNone(target, ".o_cp_action_menus span:contains(Add Properties)");
        },
    );

    QUnit.test("properties: onChange return new properties", async function (assert) {
        serverData.models.company.records[1] = {
            id: 38,
            display_name: "Company 2",
            definitions: [
                {
                    name: "property_2_1",
                    string: "My Char",
                    type: "char",
                    view_in_kanban: true,
                },
            ],
        };
        serverData.models.partner.onchanges = {
            company_id: (changes) => {
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
            },
        };
        async function mockRPC(route, { method }) {
            if (["check_access_rights", "check_access_rule"].includes(method)) {
                return true;
            }
        }

        await makeView({
            type: "form",
            resModel: "partner",
            resId: 1,
            serverData,
            arch: `
                <form>
                    <sheet>
                        <group>
                            <field name="company_id"/>
                            <field name="properties"/>
                        </group>
                    </sheet>
                </form>`,
            mockRPC,
        });

        await editInput(target, "[name='company_id'] input", "Company 2");
        await click(target.querySelector(".dropdown-menu li"));
        assert.deepEqual(
            [...target.querySelectorAll("[name='properties'] .o_property_field")].map(
                (el) => el.textContent
            ),
            ["My New Char"]
        );
        assert.deepEqual(
            [...target.querySelectorAll("[name='properties'] .o_property_field input")].map(
                (el) => el.value
            ),
            ["Hello"]
        );
    });
});
