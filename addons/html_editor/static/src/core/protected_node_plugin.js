import { Plugin } from "../plugin";
import { isProtecting, isUnprotecting } from "../utils/dom_info";
import { childNodes } from "../utils/dom_traversal";
import { withSequence } from "@html_editor/utils/resource";
import { NATIVE_MUTATION_TYPES } from "./dom_observer_plugin";

const PROTECTED_SELECTOR = `[data-oe-protected="true"],[data-oe-protected=""]`;
const UNPROTECTED_SELECTOR = `[data-oe-protected="false"]`;

/**
 * @typedef { Object } ProtectedNodeShared
 * @property { ProtectedNodePlugin['setProtectingNode'] } setProtectingNode
 */

export class ProtectedNodePlugin extends Plugin {
    static id = "protectedNode";
    static shared = ["setProtectingNode"];
    /** @type {import("plugins").EditorResources} */
    resources = {
        /** Handlers */
        on_will_filter_mutations_handlers: this.beforeFilteringMutations.bind(this),

        /** Processors */
        clean_for_save_processors: (root) => this.cleanForSave(root),
        normalize_processors: withSequence(0, this.normalize.bind(this)),

        /** Predicates */
        region_properties: {
            // avoid merge
            is: (node) => isProtecting(node) || isUnprotecting(node),
            splittable: false,
        },
        is_mutation_savable_predicates: this.isMutationSavable.bind(this),

        /** Providers */
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

    /**
     * @param {import("./dom_observer_plugin").NativeMutation[]} mutations
     */
    beforeFilteringMutations(mutations) {
        for (const mutation of mutations) {
            if (mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST) {
                if (mutation.target.nodeType !== Node.ELEMENT_NODE) {
                    return;
                }
                const addedNodes = mutation.addedNodes;
                if (
                    (this.protectedNodes.has(mutation.target) &&
                        !mutation.target.matches(UNPROTECTED_SELECTOR)) ||
                    mutation.target.matches(PROTECTED_SELECTOR)
                ) {
                    for (const addedNode of addedNodes) {
                        this.protectNode(addedNode);
                    }
                } else if (
                    !this.protectedNodes.has(mutation.target) ||
                    mutation.target.matches(UNPROTECTED_SELECTOR)
                ) {
                    for (const addedNode of addedNodes) {
                        this.unProtectNode(addedNode);
                    }
                }
            }
        }
    }

    /**
     * @param {import("./dom_observer_plugin").NativeMutation} mutation
     * @return {boolean}
     */
    isMutationSavable(mutation) {
        if (mutation.type === NATIVE_MUTATION_TYPES.CHILD_LIST) {
            if (
                (this.protectedNodes.has(mutation.target) &&
                    !mutation.target.matches(UNPROTECTED_SELECTOR)) ||
                mutation.target.matches(PROTECTED_SELECTOR)
            ) {
                return false;
            }
        } else if (this.protectedNodes.has(mutation.target)) {
            return false;
        }
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
        return elem;
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
        return clone;
    }
}
