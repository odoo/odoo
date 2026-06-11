import { Plugin } from "../plugin";
import { registry } from "@web/core/registry";

const ALLOWED_NODE_TYPES = [Node.ELEMENT_NODE, Node.TEXT_NODE];

export class ReferenceNodePlugin extends Plugin {
    static id = "referenceNode";
    static shared = ["createReferenceTreeWalker", "isAllowedReferenceNode", "processChildNodes"];

    setup() {
        this.referenceToInfo = new WeakMap();
    }

    processChildNodes(node, callback = () => {}) {
        const nodes = [];
        let child = node.firstChild;
        while (child) {
            const currentChild = child;
            child = child.nextSibling;
            if (!this.isAllowedReferenceNode(currentChild)) {
                continue;
            }
            if (callback(currentChild) !== false) {
                nodes.push(currentChild);
            }
        }
        return nodes;
    }

    isAllowedReferenceNode(node) {
        return ALLOWED_NODE_TYPES.includes(node.nodeType);
    }

    createReferenceTreeWalker(filter = () => NodeFilter.FILTER_ACCEPT) {
        return this.config.referenceDocument.createTreeWalker(
            this.config.reference,
            NodeFilter.SHOW_ELEMENT | NodeFilter.SHOW_TEXT,
            filter
        );
    }
}

registry
    .category("mail-html-conversion-core-plugins")
    .add(ReferenceNodePlugin.id, ReferenceNodePlugin);
