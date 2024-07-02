import { Plugin } from "../plugin";
import { isProtected } from "../utils/dom_info";
import { closestElement } from "../utils/dom_traversal";

export class ProtectedNodePlugin extends Plugin {
    static name = "protected_node";
    /** @type { function(ProtectedNodePlugin):Record<string, any> } **/
    static resources(p) {
        return { is_mutation_record_savable: p.isMutationRecordSavable.bind(p) };
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
                    isProtected(closestProtectedCandidate.parentElement)
                ) {
                    return false;
                }
                break;
            case "false":
                if (
                    record.type === "attributes" &&
                    record.target === closestProtectedCandidate &&
                    isProtected(closestProtectedCandidate.parentElement)
                ) {
                    return false;
                }
                break;
        }
        return true;
    }
}
