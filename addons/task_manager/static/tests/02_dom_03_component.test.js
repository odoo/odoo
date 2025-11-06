import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, edit, queryAll, queryOne, animationFrame, isVisible } from "@odoo/hoot-dom";
import { Component, useState } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

// DOM test component wrapper for AwesomeDashboard
class DOMTestTaskManager extends Component {
    static template = "task_manager.AwesomeDashboard";

    setup() {
        this.state = useState({
            tasks: [
                { id: 1, name: "Learn DOM Testing", is_done: false },
                { id: 2, name: "Master hoot-dom", is_done: true },
                { id: 3, name: "Write great tests", is_done: false },
            ],
            newTask: "",
        });
    }

    async addTask() {
        if (!this.state.newTask.trim()) {
            return;
        }
        const newTask = {
            id: Date.now(),
            name: this.state.newTask,
            is_done: false,
        };
        this.state.tasks.push(newTask);
        this.state.newTask = "";
    }

    async toggleTask(task) {
        task.is_done = !task.is_done;
    }

    async deleteTask(task) {
        this.state.tasks = this.state.tasks.filter((t) => t.id !== task.id);
    }
}

describe("Task Manager - DOM Tests (Teaching)", () => {
    beforeEach(async () => {
        await mountWithCleanup(DOMTestTaskManager);
    });

    // ============================================
    // TEACHING TEST 1: Querying and Reading DOM Elements
    // ============================================
    // This test demonstrates how to:
    // - Query DOM elements using selectors
    // - Read text content and attributes
    // - Verify element visibility
    // - Count elements in the DOM
    test("should query and read DOM elements correctly", async () => {
        // Step 1: Query a single element using queryOne
        // queryOne throws an error if element is not found
        const title = queryOne("h2.title");
        expect(title).toHaveCount(1);
        expect(title.textContent.trim()).toBe("📝 Task Manager");

        // Step 2: Query multiple elements using queryAll
        // queryAll returns an array of all matching elements
        const taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(3);

        // Step 3: Query input element and check its attributes
        const input = queryOne("input[type='text']");
        expect(input).toHaveCount(1);
        expect(input.placeholder).toBe("✍️ Add a new task...");
        expect(input.type).toBe("text");

        // Step 4: Check if elements are visible
        const addButton = queryOne(".btn-add");
        expect(isVisible(addButton)).toBe(true);
        expect(addButton.textContent.trim()).toBe("＋ Add");

        // Step 5: Query nested elements within a parent
        const firstTask = taskItems[0];
        const checkbox = firstTask.querySelector("input[type='checkbox']");
        expect(checkbox).toHaveCount(1);
        expect(checkbox.checked).toBe(false); // First task is not done

        // Step 6: Check task names are displayed correctly
        const taskNames = queryAll(".task-item span");
        expect(taskNames[0].textContent).toBe("Learn DOM Testing");
        expect(taskNames[1].textContent).toBe("Master hoot-dom");
        expect(taskNames[2].textContent).toBe("Write great tests");
    });

    // ============================================
    // TEACHING TEST 2: Interacting with DOM Elements
    // ============================================
    // This test demonstrates how to:
    // - Click buttons and checkboxes
    // - Edit input fields
    // - Wait for DOM updates after interactions
    // - Verify state changes in the DOM
    test("should interact with DOM elements and verify changes", async () => {
        // Step 1: Get initial state
        let taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(3);

        // Step 2: Interact with input field using edit()
        // edit() simulates typing in an input field
        const input = queryOne("input[type='text']");
        await click(input); // Focus the input first
        await edit("New Task Test");
        expect(input.value).toBe("New Task Test");

        // Step 3: Click the add button to add a new task
        const addButton = queryOne(".btn-add");
        await click(addButton);

        // Step 4: Wait for DOM to update after the click
        // animationFrame() waits for the next frame, ensuring DOM updates are rendered
        await animationFrame();

        // Step 5: Verify the new task was added
        taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(4);
        const newTaskName = taskItems[3].querySelector("span").textContent;
        expect(newTaskName).toBe("New Task Test");

        // Step 6: Toggle a checkbox to mark task as done
        const firstTaskCheckbox = taskItems[0].querySelector("input[type='checkbox']");
        expect(firstTaskCheckbox.checked).toBe(false);
        await click(firstTaskCheckbox);
        await animationFrame();

        // Step 7: Verify checkbox state changed
        expect(firstTaskCheckbox.checked).toBe(true);

        // Step 8: Verify delete button appears for completed tasks
        // Delete button only shows for completed tasks (is_done = true)
        const deleteButton = taskItems[0].querySelector(".btn-delete");
        expect(deleteButton).toHaveCount(1);
        expect(isVisible(deleteButton)).toBe(true);

        // Step 9: Delete a completed task
        await click(deleteButton);
        await animationFrame();

        // Step 10: Verify task was removed
        taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(3);
    });

    // ============================================
    // PRACTICE TEST 1: Complete the checkbox interaction test
    // ============================================
    /**
     * @practice
     * @hint Use queryAll to find all checkboxes
     * @hint Click a checkbox that is currently unchecked
     * @hint Use animationFrame() to wait for DOM updates
     * @hint Verify the checkbox.checked property changed
     * @hint Check that the task's span element has the "done" class after toggling
     */
    test.todo("should toggle checkbox and update task styling", async () => {
        // TODO: Write a test that:
        // 1. Finds the second task item (index 1)
        // 2. Gets its checkbox
        // 3. Verifies it's currently checked (task 2 is done)
        // 4. Clicks the checkbox to uncheck it
        // 5. Waits for animation frame
        // 6. Verifies the checkbox is now unchecked
        // 7. Verifies the task's span no longer has the "done" class
    });

    // ============================================
    // PRACTICE TEST 2: Complete the add multiple tasks test
    // ============================================
    /**
     * @practice
     * @hint Use edit() to type in the input field
     * @hint Use click() to click the add button
     * @hint Use animationFrame() after each interaction
     * @hint Use queryAll(".task-item") to count tasks
     * @hint Verify each new task appears in the list
     */
    test.todo("should add multiple tasks sequentially", async () => {
        // TODO: Write a test that:
        // 1. Starts with 3 tasks (from beforeEach setup)
        // 2. Adds a task named "Task A"
        // 3. Verifies there are now 4 tasks
        // 4. Adds a task named "Task B"
        // 5. Verifies there are now 5 tasks
        // 6. Verifies "Task A" and "Task B" appear in the correct order
        // 7. Verifies the input field is empty after each addition
    });
});
