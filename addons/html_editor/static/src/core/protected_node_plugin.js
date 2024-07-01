import { Plugin } from "../plugin";
import { isProtected, isProtecting } from "../utils/dom_info";
import { closestElement } from "../utils/dom_traversal";

export class ProtectedNodePlugin extends Plugin {
    static name = "protected_node";
    /** @type { function(ProtectedNodePlugin):Record<string, any> } **/
    static resources(p) {
        return {
            is_mutation_record_savable: p.isMutationRecordSavable.bind(p),
            filter_descendants_to_remove: p.filterDescendantsToRemove.bind(p),
        };
    }
    static shared = ["setProtectingNode"];

    handleCommand(command, payload) {
        switch (command) {
            case "NORMALIZE": {
                this.normalize(payload.node);
                break;
            }
            case "CLEAN_FOR_SAVE": {
                this.cleanForSave(payload.root);
                break;
            }
        }
    }

    filterDescendantsToRemove(elem) {
        // TODO @phoenix: history plugin can register protected nodes in its
        // id maps, should it be prevented? => if yes, take care that data-oe-protected="false"
        // elements should also be registered even though they are protected.
        if (isProtecting(elem)) {
            const descendantsToRemove = [];
            for (const candidate of elem.querySelectorAll('[data-oe-protected="false"')) {
                if (
                    candidate.closest(`[data-oe-protected="true"],[data-oe-protected=""]`) === elem
                ) {
                    descendantsToRemove.push(...candidate.childNodes);
                }
            }
            return descendantsToRemove;
        }
    }

    /**
     * @param {MutationRecord} record
     * @return {boolean}
     */
    isMutationRecordSavable(record) {
        const closestProtectedCandidate = closestElement(record.target, "[data-oe-protected]");
        if (!closestProtectedCandidate) {
            return true;
        }
        const protectedValue = closestProtectedCandidate.dataset.oeProtected;
        switch (protectedValue) {
            case "true":
            case "":
                if (
                    record.type !== "attributes" ||
                    record.target !== closestProtectedCandidate ||
                    (closestProtectedCandidate.parentElement &&
                        isProtected(closestProtectedCandidate.parentElement))
                ) {
                    return false;
                }
                break;
            case "false":
                if (
                    record.type === "attributes" &&
                    record.target === closestProtectedCandidate &&
                    closestProtectedCandidate.parentElement &&
                    isProtected(closestProtectedCandidate.parentElement) &&
                    record.attributeName !== "contenteditable"
                ) {
                    return false;
                }
                break;
        }
        return true;
    }

    forEachProtectingElem(elem, callback) {
        const selector = `[data-oe-protected]`;
        const protectingNodes = [...elem.querySelectorAll(selector)];
        if (elem.matches(selector)) {
            protectingNodes.unshift(elem);
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
        this.forEachProtectingElem(elem, this.setProtectingNode);
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
        elem.setAttribute("contenteditable", protecting ? "false" : "true");
    }

    cleanForSave(clone) {
        this.forEachProtectingElem(clone, (protectingNode) => {
            protectingNode.removeAttribute("contenteditable");
        });
    }
}
