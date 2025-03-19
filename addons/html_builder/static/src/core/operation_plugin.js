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
    next(...args) {
        return this.operation.next(...args);
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
