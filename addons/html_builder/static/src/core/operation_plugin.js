import { Plugin } from "@html_editor/plugin";
import { Operation } from "./operation";
import { useComponent } from "@odoo/owl";

/** @typedef {import("./operation").OperationParams} OperationParams */

export class OperationPlugin extends Plugin {
    static id = "operation";
    static dependencies = ["history"];
    static shared = ["next"];

    setup() {
        this.operation = new Operation(this.document);
    }

    /**
     * Executes a function (async or not) in the mutex.
     *
     * @param {Function} fn the function
     * @param {OperationParams} params
     * @returns {Promise<void>}
     */
    next(fn, params) {
        return this.operation.next(fn, params);
    }
}

export function useOperation() {
    const comp = useComponent();
    return (apply, ...args) => {
        comp.env.editor.shared.operation.next(async (...args) => {
            await apply(...args);
            comp.env.editor.shared.history.addStep();
        }, ...args);
    };
}
