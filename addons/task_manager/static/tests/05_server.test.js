import { beforeEach, describe, expect, test } from "@odoo/hoot";
import { click, edit, queryAll, queryOne, animationFrame, waitFor } from "@odoo/hoot-dom";
import { onRpc, makeMockServer, mountWithCleanup } from "@web/../tests/web_test_helpers";
import { AwesomeDashboard } from "../src/dashboard";

describe("Task Manager - Server Tests (Teaching)", () => {
    beforeEach(async () => {
        await makeMockServer();
    });

    // ============================================
    // TEACHING TEST 1: Mocking RPC Calls and Loading Data
    // ============================================
    // This test demonstrates how to:
    // - Mock RPC routes using onRpc()
    // - Test component initialization with server data
    // - Verify RPC calls are made correctly
    // - Test that component renders server data
    test("should load tasks from server on initialization", async () => {
        // Step 1: Define mock server data
        // onRpc() allows us to mock any RPC route
        // The function receives a request object and should return the response
        const mockTasks = [
            { id: 1, name: "Server Task 1", is_done: false },
            { id: 2, name: "Server Task 2", is_done: true },
            { id: 3, name: "Server Task 3", is_done: false },
        ];

        // Step 2: Mock the /task_manager/tasks route
        // This route is called in onWillStart() when component mounts
        onRpc(
            "/task_manager/tasks",
            () =>
                // Return the mock data
                mockTasks
        );

        // Step 3: Mount the component
        // The component will automatically call /task_manager/tasks in onWillStart
        await mountWithCleanup(AwesomeDashboard, { noMainContainer: true });

        // Step 4: Wait for the component to finish loading
        // waitFor() ensures the DOM is updated with server data
        await waitFor(".task-item");

        // Step 5: Verify tasks were loaded from server
        const taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(3);

        // Step 6: Verify task names match server data
        const taskNames = taskItems.map((item) => item.querySelector("span").textContent);
        expect(taskNames).toEqual(["Server Task 1", "Server Task 2", "Server Task 3"]);

        // Step 7: Verify task states match server data
        const checkboxes = taskItems.map((item) => item.querySelector("input[type='checkbox']"));
        expect(checkboxes[0].checked).toBe(false); // Task 1 not done
        expect(checkboxes[1].checked).toBe(true); // Task 2 done
        expect(checkboxes[2].checked).toBe(false); // Task 3 not done
    });

    // ============================================
    // TEACHING TEST 2: Mocking RPC Calls with Parameters
    // ============================================
    // This test demonstrates how to:
    // - Mock RPC routes that accept parameters
    // - Verify RPC calls are made with correct parameters
    // - Test adding, toggling, and deleting tasks via server
    // - Verify component updates after server responses
    test("should add, toggle, and delete tasks via server RPC calls", async () => {
        // Step 1: Set up initial server state
        let serverTasks = [{ id: 1, name: "Initial Task", is_done: false }];

        // Step 2: Mock the load tasks route
        onRpc("/task_manager/tasks", () => [...serverTasks]);

        // Step 3: Mock the add task route
        // The route receives parameters in request.json()
        onRpc("/task_manager/add_task", async (request) => {
            const { params } = await request.json();
            // Create a new task (simulating server behavior)
            const newTask = {
                id: Date.now(),
                name: params.name,
                is_done: false,
            };
            serverTasks.push(newTask);
            return newTask;
        });

        // Step 4: Mock the toggle task route
        onRpc("/task_manager/toggle_task", async (request) => {
            const { params } = await request.json();
            // Find and update the task in server state
            const task = serverTasks.find((t) => t.id === params.id);
            if (task) {
                task.is_done = params.is_done;
            }
            return true;
        });

        // Step 5: Mock the delete task route
        onRpc("/task_manager/delete_task", async (request) => {
            const { params } = await request.json();
            // Remove task from server state
            serverTasks = serverTasks.filter((t) => t.id !== params.id);
            return true;
        });

        // Step 6: Mount the component
        await mountWithCleanup(AwesomeDashboard, { noMainContainer: true });
        await waitFor(".task-item");

        // Step 7: Verify initial task is loaded
        let taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(1);
        expect(taskItems[0].querySelector("span").textContent).toBe("Initial Task");

        // Step 8: Add a new task via the UI
        const input = queryOne("input[type='text']");
        const addButton = queryOne(".btn-add");
        await click(input);
        await edit("New Server Task");
        await click(addButton);
        await animationFrame();

        // Step 9: Verify new task was added (component should update)
        await waitFor(".task-item:nth-child(2)");
        taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(2);
        expect(taskItems[1].querySelector("span").textContent).toBe("New Server Task");

        // Step 10: Toggle the first task
        const firstCheckbox = taskItems[0].querySelector("input[type='checkbox']");
        expect(firstCheckbox.checked).toBe(false);
        await click(firstCheckbox);
        await animationFrame();

        // Step 11: Verify task was toggled
        expect(firstCheckbox.checked).toBe(true);

        // Step 12: Verify delete button appears for completed task
        await animationFrame();
        const deleteButton = taskItems[0].querySelector(".btn-delete");
        expect(deleteButton).toHaveCount(1);

        // Step 13: Delete the completed task
        await click(deleteButton);
        await animationFrame();

        // Step 14: Verify task was deleted
        taskItems = queryAll(".task-item");
        expect(taskItems).toHaveLength(1);
        expect(taskItems[0].querySelector("span").textContent).toBe("New Server Task");
    });

    // ============================================
    // PRACTICE TEST: Complete the RPC parameter validation test
    // ============================================
    /**
     * @practice
     * @hint Use onRpc() to capture and verify RPC parameters
     * @hint Test that add_task receives the correct task name
     * @hint Test that toggle_task receives correct id and is_done values
     * @hint Test that delete_task receives the correct task id
     * @hint Use expect() inside the onRpc callback to verify parameters
     */
    test.todo("should send correct parameters to server RPC calls", async () => {
        // TODO: Write a test that:
        // 1. Sets up initial tasks from server
        // 2. Mocks add_task and verifies it receives the correct name parameter
        // 3. Adds a task and verifies the RPC was called with correct params
        // 4. Mocks toggle_task and verifies it receives correct id and is_done
        // 5. Toggles a task and verifies the RPC was called with correct params
        // 6. Mocks delete_task and verifies it receives the correct id
        // 7. Deletes a task and verifies the RPC was called with correct params
    });
});
