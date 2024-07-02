import { Plugin } from "../plugin";
import { closestElement } from "../utils/dom_traversal";

export class TransientNodePlugin extends Plugin {
    static name = "transient_node";
    static shared = ["isTransient"];

    isTransient(element) {
        const protectedElement = closestElement(element, "[data-oe-protected]");
        if (!protectedElement) {
            return false;
        }
        const protectedValue = protectedElement.dataset.oeProtected;
        return protectedValue === "" || protectedValue === "true";
    }

    handleCommand(command, payload) {
        switch (command) {
            case "CLEAN":
                this.clearTransients(payload.root);
                break;
        }
    }
    clearTransients(node) {
        for (const transientNode of node.querySelectorAll(
            `[data-oe-transient-content="true"], [data-oe-transient-content=""]`
        )) {
            transientNode.replaceChildren();
        }
    }
}
