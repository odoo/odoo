/** @odoo-module **/

import {
    click,
    clickDiscard,
    clickSave,
    editInput,
    getFixture,
    nextTick,
    triggerEvent,
} from "@web/../tests/helpers/utils";
import { makeView, setupViewRegistries } from "@web/../tests/views/helpers";

let serverData;
let target;

async function closePopover(target) {
    // Close the popover by clicking outside
    document.activeElement.blur();
    await click(document, "html");
}

async function changeType(target, propertyType) {
    const TYPES_INDEX = {"datetime": 6, "selection": 7, "tags": 8, "many2one": 9, "many2many": 10};
    const propertyTypeIndex = TYPES_INDEX[propertyType];
    await click(target, ".o_field_property_definition_type input");
    await nextTick();
    await click(target, `.o_field_property_definition_type .dropdown-item:nth-child(${propertyTypeIndex})`);
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
                                    view_in_kanban: true,
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
                                    view_in_kanban: true,
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
                                    view_in_kanban: true,
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
                                    view_in_kanban: true,
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
                                    view_in_kanban: true,
                                },
                            ],
                            company_id: 37,
                        },
                    ],
                },
                company: {
                    fields: {
                        name: {
                            string: "Name",
                            type: "char",
                        },
                    },
                    records: [
                        {
                            id: 37,
                            display_name: "Company 1",
                        },
                    ],
                },
                'res.users': {
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
                        }, {
                            id: 2,
                            display_name: "Bob",
                        }, {
                            id: 3,
                            display_name: "Eve",
                        },
                    ],
                },
            },
        };

        setupViewRegistries();
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
        });

        const field = target.querySelector(".o_field_properties");
        assert.ok(field, "The field must be in the view");

        const addButton = target.querySelector(".o_field_property_add button");
        assert.notOk(addButton, "The add button must not be in the view");

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
            if (method === "check_access_rights") {
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

        const addButton = target.querySelector(".o_field_property_add button");
        assert.ok(addButton, "The add button must be in the view");

        const editButton = field.querySelectorAll(".o_field_property_open_popover");
        assert.ok(editButton, "The edit definition button must be in the view");

        const property = field.querySelector(".o_property_field_value input");
        assert.strictEqual(property.value, "char value");

        // Open the definition popover
        await click(target, ".o_property_field:first-child .o_field_property_open_popover");

        const popover = target.querySelector(".o_property_field_popover");
        assert.ok(popover, "Should have opened the definition popover");

        const label = popover.querySelector(".o_field_property_definition_header input");
        assert.strictEqual(label.value, "My Char");

        const type = popover.querySelector(".o_field_property_definition_type input");
        assert.strictEqual(type.value, "Text");

        // Change the property type to "Date & Time"
        await editInput(target, ".o_field_property_definition_header input", "My Datetime");
        await changeType(target, "datetime");
        assert.strictEqual(type.value, "Date & Time", "Should have changed the property type");

        // Choosing a date in the date picker should not close the definition popover
        await click(target, ".o_field_property_definition_value .o_datepicker_input");
        await click(document, ".datepicker-days tr:first-child .day:nth-child(3)");
        assert.ok(
            document.querySelector(".picker-switch .fa-check"),
            "Should not close the definition popover after selecting a date"
        );
        await click(document, ".picker-switch .fa-check");
        assert.ok(
            target.querySelector(".o_property_field_popover"),
            "Should not close the definition popover after selecting a date"
        );

        await closePopover(target);

        // Check that the type change have been propagated
        const datetimeLabel = field.querySelector(".o_field_property_label b");
        assert.strictEqual(
            datetimeLabel.innerText,
            "My Datetime",
            "Should have updated the property label"
        );
        const datetimeComponent = field.querySelector(".o_property_field_value .o_datepicker");
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
            if (method === "check_access_rights") {
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

        const addButton = target.querySelector(".o_field_property_add button");
        assert.ok(addButton, "The add button must be in the view");

        // Create a new property
        await click(target, ".o_field_property_add button");

        await nextTick();

        const popover = target.querySelector(".o_property_field_popover");
        assert.ok(popover, "Should have opened the definition popover");

        const label = popover.querySelector(".o_field_property_definition_header input");
        assert.strictEqual(label.value, "Property 3", "Should have added a default label");

        const type = popover.querySelector(".o_field_property_definition_type input");
        assert.strictEqual(type.value, "Text", "Default type must be text");

        await closePopover(target);

        const properties = field.querySelectorAll(".o_property_field");
        assert.strictEqual(properties.length, 3);

        const newProperty = properties[2];
        const newPropertyLabel = newProperty.querySelector(".o_field_property_label");
        assert.strictEqual(newPropertyLabel.innerText, "Property 3");
    });

    /**
     * Test the selection property.
     */
    QUnit.test("properties: selection", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (method === "check_access_rights") {
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

        // Create a new selection option
        await click(target, ".o_field_property_selection .fa-plus");
        let options = popover.querySelectorAll(".o_field_property_selection_option");
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

        options = popover.querySelectorAll(".o_field_property_selection_option");
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

        assert.strictEqual(
            document.activeElement,
            options[3].querySelector("input"),
            "Should focus the previous option"
        );
        options = popover.querySelectorAll(".o_field_property_selection_option");
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
        options = popover.querySelectorAll(".o_field_property_selection_option");
        assert.strictEqual(options.length, 4, "Should not remove any options");

        // Remove the second option
        await click(target, ".o_field_property_selection_option:nth-child(2) .fa-times");
        options = popover.querySelectorAll(".o_field_property_selection_option");
        assert.strictEqual(options.length, 3, "Should have removed the second option");
        const optionValues = [...options].map((option) => option.querySelector("input").value);
        assert.deepEqual(
            optionValues,
            ["A", "C", "New option"],
            "Should have removed the second option"
        );
    });

    /**
     * Test the properties re-arrangement
     */
    QUnit.test("properties: move properties", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (method === "check_access_rights") {
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
        await click(popover, ".fa-chevron-up");
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
        await click(popover, ".fa-chevron-up");
        assert.deepEqual(getLabels(), ["My Selection", "My Char", "My Char 3", "My Char 4"]);

        // Move the property down
        await click(popover, ".fa-chevron-down");
        assert.deepEqual(getLabels(), ["My Char", "My Selection", "My Char 3", "My Char 4"]);

        // Move the property at the bottom
        await click(popover, ".fa-chevron-down");
        await click(popover, ".fa-chevron-down");
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
            if (method === "check_access_rights") {
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
            for (let i = 0; i < 50; ++i) {
                // Wait until the dropdown appears
                await nextTick();
            }
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
            if (method === "check_access_rights") {
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
        for (let i = 0; i < 50; ++i) {
            await nextTick();
        } // wait until the dropdown appears
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
            if (method === "check_access_rights") {
                return true;
            } else if (method === "get_available_models" && model === "ir.model") {
                return [
                    { model: "res.partner", display_name: "Partner" },
                    { model: "res.users", display_name: "User" },
                ];
            } else if (method === "display_name_for" && model === "ir.model" && args[0][0] === "res.users") {
                return [{"display_name": "User", "model": "res.users"}];
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
        for (let i = 0; i < 50; ++i) {
            await nextTick();
        } // wait until the dropdown appears
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

    QUnit.test("properties: date(time) property manipulations", async function (assert) {
        serverData.models.partner.records.push({
            id: 3,
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
            resId: 3,
            serverData,
            arch: `<form><field name="company_id"/><field name="properties"/></form>`,
            mockRPC(route, { method, args }) {
                assert.step(method);
                if (method === "check_access_rights") {
                    return true;
                }
                if (method === "write") {
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
                            value: "2018-12-31 11:01:01",
                        },
                    ]);
                }
            },
        });
        assert.verifySteps(["get_views", "read", "check_access_rights"]);

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
        await click(document.body, ".datepicker [data-day='12/31/2018']");
        assert.equal(target.querySelector("[property-name=property_1] input").value, "12/31/2018");

        // edit date time property
        await click(target, ".o_property_field[property-name=property_2] input");
        await click(document.body, ".datepicker [data-day='12/31/2018']");
        await click(document.body, ".picker-switch [data-action=togglePicker]");
        await click(document.body, ".timepicker [data-action=incrementHours]");
        await click(document.body, ".timepicker [data-action=incrementMinutes]");
        await click(document.body, ".timepicker [data-action=incrementSeconds]");
        await click(document.body, ".picker-switch [data-action=close]");
        assert.equal(
            target.querySelector("[property-name=property_2] input").value,
            "12/31/2018 12:01:01"
        );

        // save
        assert.verifySteps([]);
        await clickSave(target);
        assert.verifySteps(["write", "read"]);
    });

    /**
     * Changing the type or the model of a property must regenerate it's name.
     * (so if we change the type / model, all other property values on other records
     * are set to False).
     * Resetting the old model / type should reset the original name.
     */
    QUnit.test("properties: name reset", async function (assert) {
        async function mockRPC(route, { method, model, kwargs }) {
            if (method === "check_access_rights") {
                return true;
            } else if (method === "get_available_models" && model === "ir.model") {
                return [
                    { model: "res.partner", display_name: "Partner" },
                    { model: "res.users", display_name: "User" },
                ];
            } else if (method === "display_name_for" && model === "ir.model") {
                return [
                    {"display_name": "User", "model": "res.users"},
                    {"display_name": "Partner", "model": "res.partner"},
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
        const property3 = target.querySelector(".o_kanban_record:nth-child(2) .o_kanban_property_field:nth-child(3) span");
        assert.notEqual(property3.innerText, "char value 3",
            "The third property should not be visible in the kanban view");
        assert.equal(property3.innerText, "char value 4");
        const property1 = target.querySelector(".o_kanban_record:nth-child(2) .o_kanban_property_field:nth-child(1) span");
        assert.equal(property1.innerText, "char value");
        const property2 = target.querySelector(".o_kanban_record:nth-child(2) .o_kanban_property_field:nth-child(2) span");
        assert.equal(property2.innerText, "C");

        // check first card
        const items = target.querySelectorAll(".o_kanban_record:nth-child(1) .o_kanban_property_field");
        assert.equal(items.length, 2);
    });
});
