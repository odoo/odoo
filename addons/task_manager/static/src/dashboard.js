import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

export class AwesomeDashboard extends Component {
    static template = "task_manager.AwesomeDashboard";

    setup() {
        this.state = useState({ tasks: [], newTask: "" });
        this.deleteTask = this.deleteTask.bind(this);
        onWillStart(async () => {
            this.state.tasks = await rpc("/task_manager/tasks");
        });
    }

    async addTask() {
        if (!this.state.newTask.trim()) {
            return;
        }
        const task = await rpc("/task_manager/add_task", {
            name: this.state.newTask,
        });
        this.state.tasks.push(task);
        this.state.newTask = "";
    }

    async toggleTask(task) {
        task.is_done = !task.is_done;
        await rpc("/task_manager/toggle_task", { id: task.id, is_done: task.is_done });
    }

    async deleteTask(task) {
        await rpc("/task_manager/delete_task", { id: task.id });
        this.state.tasks = this.state.tasks.filter((t) => t.id !== task.id);
    }
}

registry.category("actions").add("task_manager.dashboard", AwesomeDashboard);
