import { Plugin } from "../plugin";
import { isProtecting, isUnprotecting } from "../utils/dom_info";
import { childNodes } from "../utils/dom_traversal";

const PROTECTED_SELECTOR = `[data-oe-protected="true"],[data-oe-protected=""]`;
const UNPROTECTED_SELECTOR = `[data-oe-protected="false"]`;

/**
 * @typedef { Object } ProtectedNodeShared
 * @property { ProtectedNodePlugin['setProtectingNode'] } setProtectingNode
 */

export class ProtectedNodePlugin extends Plugin {
    static id = "protectedNode";
    static shared = ["setProtectingNode"];
    resources = {
        /** Handlers */
        clean_for_save_handlers: ({ root }) => this.cleanForSave(root),
        normalize_handlers: this.normalize.bind(this),
        before_filter_mutation_record_handlers: this.beforeFilteringMutationRecords.bind(this),

        unsplittable_node_predicates: [
            isProtecting, // avoid merge
            isUnprotecting,
        ],
        savable_mutation_record_predicates: this.isMutationRecordSavable.bind(this),
        removable_descendants_providers: this.filterDescendantsToRemove.bind(this),
    };

    setup() {
        this.protectedNodes = new WeakSet();
    }

    filterDescendantsToRemove(elem) {
        // TODO @phoenix: history plugin can register protected nodes in its
        // id maps, should it be prevented? => if yes, take care that data-oe-protected="false"
        // elements should also be registered even though they are protected.
        if (isProtecting(elem)) {
            const descendantsToRemove = [];
            for (const candidate of elem.querySelectorAll(UNPROTECTED_SELECTOR)) {
                if (candidate.closest(PROTECTED_SELECTOR) === elem) {
                    descendantsToRemove.push(...childNodes(candidate));
                }
            }
            return descendantsToRemove;
        }
    }

    protectNode(node) {
        if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.matches(UNPROTECTED_SELECTOR)) {
                this.unProtectDescendants(node);
            } else if (!this.protectedNodes.has(node)) {
                this.protectDescendants(node);
            }
            // assume that descendants are already handled if the node
            // is already protected.
        }
        this.protectedNodes.add(node);
    }

    unProtectNode(node) {
        if (node.nodeType === Node.ELEMENT_NODE) {
            if (node.matches(PROTECTED_SELECTOR)) {
                this.protectDescendants(node);
            } else if (this.protectedNodes.has(node)) {
                this.unProtectDescendants(node);
            }
            // assume that descendants are already handled if the node
            // is already not protected.
        }
        this.protectedNodes.delete(node);
    }

    protectDescendants(node) {
        let child = node.firstChild;
        while (child) {
            this.protectNode(child);
            child = child.nextSibling;
        }
    }

    unProtectDescendants(node) {
        let child = node.firstChild;
        while (child) {
            this.unProtectNode(child);
            child = child.nextSibling;
        }
    }

    beforeFilteringMutationRecords(records) {
        for (const record of records) {
            if (record.type === "childList") {
                if (record.target.nodeType !== Node.ELEMENT_NODE) {
                    return;
                }
                if (
                    (this.protectedNodes.has(record.target) &&
                        !record.target.matches(UNPROTECTED_SELECTOR)) ||
                    record.target.matches(PROTECTED_SELECTOR)
                ) {
                    for (const addedNode of record.addedNodes) {
                        this.protectNode(addedNode);
                    }
                } else if (
                    !this.protectedNodes.has(record.target) ||
                    record.target.matches(UNPROTECTED_SELECTOR)
                ) {
                    for (const addedNode of record.addedNodes) {
                        this.unProtectNode(addedNode);
                    }
                }
            }
        }
    }

    /**
     * @param {MutationRecord} record
     * @return {boolean}
     */
    isMutationRecordSavable(record) {
        if (record.type === "attributes") {
            if (record.attributeName === "contenteditable") {
                return (
                    !this.protectedNodes.has(record.target) ||
                    record.target.matches(UNPROTECTED_SELECTOR)
                );
            }
        } else if (record.target.nodeType === Node.ELEMENT_NODE) {
            return !(
                (this.protectedNodes.has(record.target) &&
                    !record.target.matches(UNPROTECTED_SELECTOR)) ||
                record.target.matches(PROTECTED_SELECTOR)
            );
        }
        return !this.protectedNodes.has(record.target);
    }

    forEachProtectingElem(elem, callback) {
        const selector = `[data-oe-protected]`;
        const protectingNodes = [...elem.querySelectorAll(selector)].reverse();
        if (elem.matches(selector)) {
            protectingNodes.push(elem);
        }
        for (const protectingNode of protectingNodes) {
            if (protectingNode.dataset.oeProtected === "false") {
                callback(protectingNode, false);
            } else {
                callback(protectingNode, true);
            }
        }
    }

    normalize(elem) {
        this.forEachProtectingElem(elem, this.setProtectingNode.bind(this));
    }

    setProtectingNode(elem, protecting) {
        elem.dataset.oeProtected = protecting;
        // contenteditable attribute is set on (un)protecting nodes for
        // implementation convenience. This could be removed but the editor
        // should be adapted to handle some use cases that are handled for
        // contenteditable elements. Currently unsupported configurations:
        // 1) unprotected non-editable content: would typically be added/removed
        // programmatically and shared in collaboration => some logic should
        // be added to handle undo/redo properly for consistency.
        // -> A adds content, A replaces his content with a new one, B replaces
        //   content of A with his own, A undo => there is now the content of B
        //   and the old content of A in the node, is it still coherent?
        // 2) protected editable content: need a specification of which
        // functions of the editor are allowed to work (and how) in that
        // editable part (none?) => should be enforced.
        if (protecting) {
            elem.setAttribute("contenteditable", "false");
            this.protectDescendants(elem);
        } else {
            elem.setAttribute("contenteditable", "true");
            this.unProtectDescendants(elem);
        }
    }

    cleanForSave(clone) {
        this.forEachProtectingElem(clone, (protectingNode) => {
            protectingNode.removeAttribute("contenteditable");
        });
    }
}
