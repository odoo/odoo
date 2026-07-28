/** @odoo-module **/

import { KanbanCompiler } from "@web/views/kanban/kanban_compiler";
import { append, createElement } from "@web/core/utils/xml";

export class ProjectTaskKanbanCompiler extends KanbanCompiler {
    setup() {
        super.setup();
        this.subtaskListComponentCompiled = {
            button: false,
            component: false,
        };
        this.compilers.push(
            { selector: ".subtask_list_button", fn: this.compileSubtaskListButton },
            { selector: "div.kanban_bottom_subtasks_section", fn: this.compileSubtaskListComponent },
        );
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileSubtaskListButton(el) {
        this.subtaskListComponentCompiled.button = true;
        el.setAttribute("t-on-click", `() => __comp__.state.folded = !__comp__.state.folded`);
        const compiled = createElement(el.nodeName);
        for (const { name, value } of el.attributes) {
            compiled.setAttribute(name, value);
        }

        for (const child of el.childNodes) {
            append(compiled, this.compileNode(child));
        }

        return compiled;
    }

    /**
     * @param {Element} el
     * @returns {Element}
     */
    compileSubtaskListComponent(el) {
        this.subtaskListComponentCompiled.component = true;
        el.setAttribute("t-if", `!__comp__.state.folded and !selection_mode`);
        const compiled = createElement(el.nodeName);
        for (const { name, value } of el.attributes) {
            compiled.setAttribute(name, value);
        }
        const listContainer = createElement('widget');
        const listElemenent = createElement('SubtaskKanbanList');
        listElemenent.setAttribute("record", '__comp__.props.record');

        append(listContainer, listElemenent);
        append(compiled, listContainer);

        return compiled;
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
