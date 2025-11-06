/** @odoo-module */

import { expect, test } from "@odoo/hoot";
import { queryOne } from "@odoo/hoot-dom";
import {
    defineModels,
    fields,
    models,
    mountWithCleanup,
    onRpc,
} from "@web/../tests/web_test_helpers";
import { View } from "@web/views/view";

// ============================================
// DEMO MODEL: Task Model
// ============================================
// Simple standalone model with basic field types only
// No external dependencies - completely self-contained
class Task extends models.Model {
    _name = "task";

    name = fields.Char({ string: "Task Name" });
    description = fields.Text({ string: "Description" });
    priority = fields.Selection({
        string: "Priority",
        selection: [
            ["low", "Low"],
            ["medium", "Medium"],
            ["high", "High"],
        ],
    });
    is_done = fields.Boolean({ string: "Done" });

    _records = [
        {
            id: 1,
            name: "Learn Odoo",
            description: "Study Odoo framework",
            priority: "high",
            is_done: false,
        },
        {
            id: 2,
            name: "Write tests",
            description: "Practice writing tests",
            priority: "medium",
            is_done: true,
        },
        {
            id: 3,
            name: "Build app",
            description: "Create a new application",
            priority: "low",
            is_done: false,
        },
    ];

    _views = {
        form: /* xml */ `
            <form>
                <sheet>
                    <group>
                        <field name="name" placeholder="Enter task name..."/>
                        <field name="priority" widget="radio" options="{'horizontal': true}"/>
                        <field name="is_done"/>
                    </group>
                    <group>
                        <field name="description" placeholder="Enter description..."/>
                    </group>
                </sheet>
            </form>
        `,
        list: /* xml */ `
            <list>
                <field name="name"/>
                <field name="priority"/>
                <field name="is_done"/>
            </list>
        `,
    };
}

// Required for list view controller
onRpc("has_group", () => true);

// ============================================
// TEACHING TEST 1: Form View Basics
// ============================================
test("form view displays task data correctly", async () => {
    defineModels([Task]);

    await mountWithCleanup(View, {
        props: {
            type: "form",
            resId: 1,
            resModel: "task",
        },
    });

    // Step 1: Verify form is rendered
    expect(".o_form_view").toHaveCount(1);

    // Step 2: Verify name field displays correct value
    const nameField = queryOne("input#name_0");
    expect(nameField).toHaveCount(1);
    expect(nameField.value).toBe("Learn Odoo");

    // Step 3: Verify description field displays correct value
    const descriptionField = queryOne("textarea#description_0");
    expect(descriptionField).toHaveCount(1);
    expect(descriptionField.value).toBe("Study Odoo framework");

    // Step 4: Verify priority field shows correct selection
    const priorityField = queryOne("input#radio_field_0_medium");
    expect(priorityField).toHaveCount(1);

    // Step 5: Verify is_done checkbox shows correct state
    const doneCheckbox = queryOne("input#is_done_0");
    expect(doneCheckbox).toHaveCount(1);
    expect(doneCheckbox.checked).toBe(false);
});

// ============================================
// TEACHING TEST 2: Form View Editing
// ============================================
test.todo("form view allows editing task fields", async () => {
    // Step 1: Edit the name field
    // Step 2: Edit the description field
    // Step 3: Change priority selection
    // Step 4: Toggle the is_done checkbox
});

// ============================================
// TEACHING TEST 3: List View Basics
// ============================================
test.todo("list view displays all tasks correctly", async () => {
    // Step 1: Verify list view is rendered
    // Step 2: Verify all task names are displayed
    // Step 3: Verify priorities are displayed
    // Step 4: Verify checkboxes show correct states
    // Step 5: Verify column headers
});
