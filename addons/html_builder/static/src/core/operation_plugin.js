import { Plugin } from "@html_editor/plugin";
import { Operation } from "./operation";
import { useComponent } from "@odoo/owl";

/** @typedef {import("./operation").OperationParams} OperationParams */

/**
 * @typedef { Object } OperationShared
 * @property { OperationPlugin['next'] } next
 */

export class OperationPlugin extends Plugin {
    static id = "operation";
    static dependencies = ["history"];
    static shared = ["next"];

    setup() {
        this.operation = new Operation(this.document);

        // Revert any potential preview as soon as the user does anything, to
        // avoid losing what the user will have done when they ends the preview.
        // If there is async action ongoing, like an async apply from a preview,
        // this may lose the user input while the apply was running
        this.addDomListener(this.editable, "keydown", () => this.next());
        this.addDomListener(this.editable, "beforeinput", () => this.next());
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
