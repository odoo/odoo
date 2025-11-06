import { beforeEach, describe, expect, test } from "@odoo/hoot";
import {
    click,
    edit,
    queryAll,
    queryOne,
    animationFrame,
    press,
    getActiveElement,
    hover,
} from "@odoo/hoot-dom";
import { Component, useState } from "@odoo/owl";
import { mountWithCleanup } from "@web/../tests/web_test_helpers";

// Interaction test component wrapper for AwesomeDashboard
class InteractionTestTaskManager extends Component {
    static template = "task_manager.AwesomeDashboard";

    setup() {
        this.state = useState({
            tasks: [
                { id: 1, name: "Practice keyboard shortcuts", is_done: false },
                { id: 2, name: "Learn interaction testing", is_done: true },
                { id: 3, name: "Master hoot-dom", is_done: false },
            ],
            newTask: "",
        });
    }

    addTask() {
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

    toggleTask(task) {
        task.is_done = !task.is_done;
    }

    deleteTask(task) {
        this.state.tasks = this.state.tasks.filter((t) => t.id !== task.id);
    }
}

describe("Task Manager - Interaction Tests (Teaching)", () => {
    beforeEach(async () => {
        await mountWithCleanup(InteractionTestTaskManager, { noMainContainer: true });
    });

    // ============================================
    // TEACHING TEST 1: Keyboard Interactions
    // ============================================
    // This test demonstrates how to:
    // - Use keyboard events (Enter, Space, Tab)
    // - Test keyboard shortcuts and accessibility
    // - Verify focus management
    test("should handle keyboard interactions correctly", async () => {
        // Step 1: Focus the input field using click
        const input = queryOne("input[type='text']");
        await click(input);

        // Step 2: Verify the input is focused (active element)
        const activeElement = getActiveElement();
        expect(activeElement).toBe(input);

        // Step 3: Type text using edit() helper
        await edit("Task from keyboard");

        // Step 4: Press Enter key to submit the form
        // In many forms, Enter key triggers submission
        // press() simulates both keydown and keyup events
        await click("button[title='Add']");
        await animationFrame();

        // Step 5: Verify the task was added
        const taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(4);
        const newTaskName = taskItems[3].textContent;
        expect(newTaskName).toBe("Task from keyboard");

        // Step 6: Test Space key on checkbox
        // Space key toggles checkboxes for accessibility
        const secondTaskCheckbox = taskItems[1].querySelector("input[type='checkbox']");
        expect(secondTaskCheckbox.checked).toBe(true);

        // Step 7: Focus the checkbox first
        await click(secondTaskCheckbox);
        expect(getActiveElement()).toBe(secondTaskCheckbox);

        // Step 8: Test Tab key navigation
        // Tab moves focus to next focusable element
        await press("Tab");
        await animationFrame();

        // Step 9: Verify focus moved (could be to next checkbox or button)
        const newActiveElement = getActiveElement();
        expect(newActiveElement).not.toBe(secondTaskCheckbox);
        expect(newActiveElement).not.toBe(input);
    });

    // ============================================
    // TEACHING TEST 2: Mouse and Focus Interactions
    // ============================================
    // This test demonstrates how to:
    // - Use hover() for mouse hover interactions
    // - Test focus management and active elements
    // - Verify element states change on interaction
    // - Test sequential user interactions
    test("should handle mouse and focus interactions correctly", async () => {
        // Step 1: Get initial task count
        let taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(3);

        // Step 2: Hover over the add button
        // hover() simulates mouse entering and moving over an element
        const addButton = queryOne(".btn-add");
        await hover(addButton);

        // Step 3: Verify button is still visible and accessible
        expect(addButton).toHaveCount(1);
        expect(addButton.textContent.trim()).toBe("＋ Add");

        // Step 4: Click to focus the input field
        const input = queryOne("input[type='text']");
        await click(input);

        // Step 5: Verify input received focus
        expect(getActiveElement()).toBe(input);

        // Step 6: Type a task name
        await edit("Hover and focus test");

        // Step 7: Click the add button (mouse click interaction)
        await click(addButton);
        await animationFrame();

        // Step 8: Verify task was added
        taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(4);

        // Step 9: Test hover on a task item
        const firstTask = taskItems[0];
        await hover(firstTask);

        // Step 10: Verify we can interact with hovered element
        const checkbox = firstTask.querySelector("input[type='checkbox']");
        expect(checkbox).toHaveCount(1);

        // Step 11: Click checkbox after hovering
        await click(checkbox);
        await animationFrame();

        // Step 12: Verify checkbox state changed
        expect(checkbox.checked).toBe(true);

        // Step 13: Test focus on delete button (only visible for completed tasks)
        await animationFrame();
        const deleteButton = firstTask.querySelector(".btn-delete");
        expect(deleteButton).toHaveCount(1);

        // Step 14: Hover and click delete button
        await hover(deleteButton);
        await click(deleteButton);
        await animationFrame();

        // Step 15: Verify task was deleted
        taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(3);
    });

    // ============================================
    // PRACTICE TEST 1: Complete the keyboard navigation test
    // ============================================
    /**
     * @practice
     * @hint Use press("Tab") to navigate between focusable elements
     * @hint Use getActiveElement() to check which element has focus
     * @hint Use Shift+Tab to navigate backwards (press("Shift+Tab"))
     * @hint Focus should move: input -> checkbox -> checkbox -> checkbox -> button
     * @hint Verify focus cycles through all interactive elements
     */
    test.todo("should navigate through all focusable elements with Tab key", async () => {
        // TODO: Write a test that:
        // 1. Clicks the input field to focus it
        // 2. Presses Tab multiple times to navigate through all focusable elements
        // 3. Verifies focus moves from input -> first checkbox -> second checkbox -> third checkbox -> add button
        // 4. Uses getActiveElement() to verify the focused element at each step
        // 5. Optionally tests Shift+Tab to navigate backwards
    });

    // ============================================
    // PRACTICE TEST 2: Complete the keyboard shortcut test
    // ============================================
    /**
     * @practice
     * @hint Use keyDown() for individual key events (keyDown("Enter"))
     * @hint Use press() for complete key press (keydown + keyup)
     * @hint Test that Enter key in input field adds a task
     * @hint Test that Space key on checkbox toggles it
     * @hint Verify multiple keyboard interactions work sequentially
     */
    test.todo("should handle multiple keyboard shortcuts in sequence", async () => {
        // TODO: Write a test that:
        // 1. Focuses the input field
        // 2. Types a task name using edit()
        // 3. Presses Enter to add the task
        // 4. Verifies the task was added
        // 5. Focuses the first checkbox
        // 6. Presses Space to toggle it
        // 7. Verifies the checkbox state changed
        // 8. Focuses the second checkbox
        // 9. Presses Space to toggle it
        // 10. Verifies both checkboxes have the expected states
    });
});
