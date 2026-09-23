import { memoize } from "@web/core/utils/functions";
import { findOperationTarget, parseTargetArch } from "./utils";

/**
 * @typedef {Object} LocatedOperation an operation of a view with an
 *  `inherit_id`, located in the arch of one of its ancestors (the view it
 *  changes)
 * @property {number} targetId the id of the view it changes
 * @property {Object} view the view the operation belongs to
 * @property {Element} operation
 * @property {number} index the index of the operation in the view's arch
 *  (see `parseTargetArch`)
 */

/**
 * The target of each operation of a view with an `inherit_id` is looked for in
 * the arch of its ancestors, up to the first primary one (the views above it are not
 * changed by it, see `_combine` in ir_ui_view.py). The whole inheritance is
 * not computed, so this is a best effort: a target added by a view out of
 * the ancestors is not found, and a target found in several ancestors is
 * ambiguous. Such operations are not located.
 *
 * @param {Object<number, Object>} views the views, indexed by id
 * @returns {LocatedOperation[]} the located operations
 */
export function locateOperations(views) {
    const getParsedArch = memoize(parseTargetArch);

    const locatedOperations = [];
    for (const view of Object.values(views)) {
        // Root and primary views do not change other views.
        if (!view.inherit_id || view.mode === "primary") {
            continue;
        }
        const ancestors = getAncestors(views, view);
        const operations = getParsedArch(view)?.operations || [];
        for (const [index, operation] of operations.entries()) {
            const owners = ancestors.filter((ancestor) => {
                const parsed = getParsedArch(ancestor);
                return parsed && findOperationTarget(parsed.root, parsed.operations, operation);
            });
            if (owners.length === 1) {
                locatedOperations.push({ targetId: owners[0].id, view, operation, index });
            }
        }
    }
    return locatedOperations;
}

/**
 * @param {Object<number, Object>} views
 * @param {Object} view
 * @returns {Object[]} the ancestors of the view, closest first, up to the
 *  first primary one
 */
function getAncestors(views, view) {
    const ancestors = [];
    let ancestor = views[view.inherit_id[0]];
    while (ancestor) {
        ancestors.push(ancestor);
        if (ancestor.mode === "primary") {
            break;
        }
        ancestor = views[ancestor.inherit_id?.[0]];
    }
    return ancestors;
}
