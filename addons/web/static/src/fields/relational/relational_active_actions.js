// @ts-check

/** @module @web/fields/relational/relational_active_actions - Reactive OWL hook for computing x2many field CRUD permissions */

import { onWillUpdateProps, useComponent } from "@odoo/owl";
import { Domain } from "@web/core/domain";

/**
 * @typedef {Object} RelationalActiveActions {
 * @property {"x2m"} type
 * @property {boolean} create
 * @property {boolean} createEdit
 * @property {boolean} delete
 * @property {boolean} [link]
 * @property {boolean} [unlink]
 * @property {boolean} [write]
 * @property {Function | null} onDelete
 */

const STANDARD_ACTIVE_ACTIONS = [
    "create",
    "createEdit",
    "delete",
    "link",
    "unlink",
    "write",
];

/**
 * Reactive OWL hook for x2m field CRUD permissions. Complements the static
 * `getActiveActions()` in `@web/views/view_utils` which parses view-level XML attributes.
 * The two are intentionally separate: view-level actions are parsed once at arch parse
 * time, while field-level actions are evaluated reactively against domain expressions
 * and fed through `subViewActiveActions`.
 *
 * @param {Object} params
 * @param {string} params.fieldType
 * @param {Record<string, boolean>} [params.subViewActiveActions={}]
 * @param {Object} [params.crudOptions={}]
 * @param {(props: Record<string, any>) => Record<any, any>} [params.getEvalParams=() => ({})]
 * @returns {RelationalActiveActions}
 */
export function useActiveActions({
    fieldType,
    subViewActiveActions = {},
    crudOptions = {},
    getEvalParams = () => ({}),
}) {
    const compute = ({ evalContext = {}, readonly = true }) => {
        const result = /** @type {RelationalActiveActions} */ ({
            type: /** @type {any} */ (fieldType),
            onDelete: null,
        });
        const evalAction = (actionName) => evals[actionName](evalContext);

        // We need to take care of tags "control" and "create" to set create stuff
        result.create = !readonly && evalAction("create");
        result.createEdit = !readonly && result.create && crudOptions.createEdit; // always a boolean
        /** @type {any} */ (result).edit = crudOptions.edit; // always a boolean
        result.delete = !readonly && evalAction("delete");
        result.write = (isMany2Many || !readonly) && evalAction("write");

        if (isMany2Many) {
            result.link = !readonly && evalAction("link");
            result.unlink = !readonly && evalAction("unlink");
        }

        if (result.unlink || (!isMany2Many && result.delete)) {
            result.onDelete = crudOptions.onDelete;
        }

        return result;
    };

    const props = useComponent().props;
    const isMany2Many = fieldType === "many2many";

    // Define eval functions
    const evals = {};
    for (const actionName of STANDARD_ACTIVE_ACTIONS) {
        /** @type {(evalContext?: any) => boolean} */
        let evalFn = () => true;
        if (crudOptions[actionName] != null) {
            const action = crudOptions[actionName];
            evalFn = (evalContext) =>
                Boolean(action && new Domain(action).contains(evalContext));
        }

        if (actionName in subViewActiveActions) {
            const viewActiveAction = subViewActiveActions[actionName];
            evals[actionName] = (evalContext) =>
                viewActiveAction && evalFn(evalContext);
        } else {
            evals[actionName] = evalFn;
        }
    }

    // Compute active actions
    const activeActions = compute(getEvalParams(props));
    onWillUpdateProps(
        /** @type {any} */ (
            (nextProps) => {
                Object.assign(activeActions, compute(getEvalParams(nextProps)));
            }
        ),
    );

    return activeActions;
}
