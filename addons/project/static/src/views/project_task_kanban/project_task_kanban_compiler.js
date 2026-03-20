import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";

export class ProjectTaskKanbanCompiler extends KanbanCompiler {
    setup() {
        super.setup();
        this.subtaskListComponentCompiled = {
            button: false,
            component: false,
        };
        this.compilers.unshift(
            { selector: 'widget[name="subtask_counter"]', fn: this.compileSubtaskListButton },
            { selector: 'widget[name="subtask_kanban_list"]', fn: this.compileSubtaskListComponent },
        );
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileSubtaskListButton(el) {
        this.subtaskListComponentCompiled.button = true;
        return this.compileWidget(el);
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileSubtaskListComponent(el) {
        this.subtaskListComponentCompiled.component = true;
        return this.compileWidget(el);
    }

    /**
     * @override
     */
    compile(key, params = {}) {
        const newRoot = super.compile(key, params);
        if (this.subtaskListComponentCompiled.component !== this.subtaskListComponentCompiled.button) {
            // Error since one of them is not compiled
            throw new Error("The subtask list component cannot be rendered if the button and the component are not in the view definition.");
        }
        return newRoot;
    }
}
