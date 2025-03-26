import { Plugin } from "@html_editor/plugin";
import { Operation } from "./operation";
import { useComponent } from "@odoo/owl";

export class OperationPlugin extends Plugin {
    static id = "operation";
    static dependencies = ["history"];
    static shared = ["next"];

    setup() {
        this.operation = new Operation();
    }
    next(fn, ...args) {
        // this code nullify every operation if the iframe
        // has been reloaded, and does not have a browsing context anymore
        const f = (result) => {
            if (fn && this.editable.ownerDocument.defaultView) {
                fn(result);
            }
        };
        return this.operation.next(f, ...args);
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
