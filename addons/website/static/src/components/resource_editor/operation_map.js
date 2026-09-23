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
 * Given a view with an `inherit_id`, look for the target of every of its
 * operations in the arch of its ancestors (stopping at the first primary
 * view).
 *
 * This is a best-effort attempt to locate the vast majority of targets, but
 * some complex inheritance schemes may be missed. For example, it does not
 * find a target added by a view out of the ancestors line. To be able to
 * locate every possible target would require to fully replicate the
 * server-side logic about inheritance composition, and a single change in the
 * future may lead to wrong results.
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
            // Skip the operation if more than one target is found (the server
            // has its own logic to decide which one to pick, but we don't
            // reproduce it).
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
