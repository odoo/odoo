import { Plugin } from "@html_editor/plugin";
import { Operation } from "./operation";

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
