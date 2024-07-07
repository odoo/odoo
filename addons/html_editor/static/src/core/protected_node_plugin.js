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
            case "BEFORE_FILTERING_MUTATION_RECORDS": {
                this.beforeFilteringMutationRecords(payload.records);
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

    beforeFilteringMutationRecords(records) {
        this.nodeToClone = new Map();
        this.cloneTree = new DocumentFragment();
        this.records = [...records];
        this.recordIndex = 0;
    }

    /**
     * Look ahead in mutation records to find where a node was removed from
     * its parent. Returns its previous parent before removal. This is useful
     * to retrace a removed hierarchy at the time of removal.
     *
     * @param {HTMLElement} target
     * @param {Number} recordIndex
     * @returns {HTMLElement|null} previous parent
     */
    findTargetParent(target, recordIndex) {
        for (const record of this.records.slice(recordIndex + 1)) {
            if (record.type === "childList") {
                for (const removedNode of record.removedNodes) {
                    if (removedNode === target) {
                        return record.target;
                    }
                }
            }
        }
        return null;
    }

    /**
     * Retrace the branch up to odoo-editor-editable for a removed node and
     * store it in a cloned tree. This will be used to determine if a mutation
     * was protected at the time it happened, depending on the older
     * configuration of nodes.
     *
     * WARNINGS:
     * 1) this function does not take attributes into account, once a node
     * is given the `data-oe-protected` attribute, it is supposed to keep the
     * same value for the entire edition session.
     * 2) children are appended in the clone without considering order, since
     * the protected feature does not care for ordering of children, therefore
     * the cloned tree is inexact but sufficient.
     *
     * This function can be refactored to handle both warnings when necessary.
     *
     * @param {Number} recordIndex
     */
    updateCloneTree(recordIndex) {
        const record = this.records[recordIndex];
        if (record.type !== "childList" || !record.removedNodes.length) {
            return;
        }
        let clone;
        let children = [];
        for (const removedNode of record.removedNodes) {
            clone = this.nodeToClone.get(removedNode);
            if (clone) {
                clone.remove();
            } else {
                clone = removedNode.cloneNode();
                this.nodeToClone.set(removedNode, clone);
            }
            children.push(clone);
        }
        let ancestor = record.target;
        clone = this.nodeToClone.get(ancestor);
        if (clone) {
            clone.append(...children);
        }
        while (!clone) {
            clone = ancestor.cloneNode();
            this.nodeToClone.set(ancestor, clone);
            clone.append(...children);
            if (clone.classList.contains("odoo-editor-editable")) {
                if (!this.cloneTree.childNodes.length) {
                    this.cloneTree.append(clone);
                }
                break;
            }
            const current = ancestor;
            ancestor = ancestor.parentElement;
            if (!ancestor) {
                ancestor = this.findTargetParent(current, recordIndex);
                if (!ancestor) {
                    // If ancestor can not be found, it means that the
                    // record removing current from its ancestor is missing
                    // from this.records. In that case, the entire branch
                    // won't be added to the cloneTree. This will likely
                    // never happen.
                    break;
                }
            }
            const ancestorClone = this.nodeToClone.get(ancestor);
            if (ancestorClone) {
                ancestorClone.append(clone);
                break;
            }
            children = [clone];
            clone = undefined;
        }
    }

    /**
     * @param {MutationRecord} record
     * @return {boolean}
     */
    isMutationRecordSavable(record) {
        const recordIndex = this.records.findIndex((item) => item === record);
        while (this.recordIndex <= recordIndex) {
            // Maintain the hierarchy for removed nodes, to evaluate if a mutation
            // was protected when it happened in its old nodes configuration.
            this.updateCloneTree(this.recordIndex);
            this.recordIndex += 1;
        }
        // If a target exists in the cloneTree, use its clone instead to
        // determine if a mutation is protected or not.
        const target = this.nodeToClone.get(record.target) || record.target;
        const closestProtectedCandidate = closestElement(target, "[data-oe-protected]");
        if (!closestProtectedCandidate) {
            return true;
        }
        const protectedValue = closestProtectedCandidate.dataset.oeProtected;
        switch (protectedValue) {
            case "true":
            case "":
                if (
                    record.type !== "attributes" ||
                    target !== closestProtectedCandidate ||
                    isProtected(closestProtectedCandidate)
                ) {
                    return false;
                }
                break;
            case "false":
                if (
                    record.type === "attributes" &&
                    target === closestProtectedCandidate &&
                    isProtected(closestProtectedCandidate) &&
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
