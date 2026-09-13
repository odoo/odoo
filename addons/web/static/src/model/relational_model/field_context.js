// @ts-check
/** @odoo-module native */

import { makeLogger } from "@web/core/debug/debug_logger";
import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { deepEqual, shallowEqual } from "@web/core/utils/collections/objects";

const CONTEXT_MEMO = new WeakMap();
const log = makeLogger("web.model.field_context");

function computeFieldContext(record, fieldName, rawContext) {
    const context = {};
    for (const key of Object.keys(record.context)) {
        if (
            !key.startsWith("default_") &&
            !key.startsWith("search_default_") &&
            !key.endsWith("_view_ref")
        ) {
            context[key] = record.context[key];
        }
    }

    const archContext =
        rawContext && rawContext !== "{}"
            ? evaluateExpr(rawContext, record.evalContext)
            : {};
    return {
        ...context,
        ...record.fields[fieldName].context,
        ...archContext,
    };
}

/**
 * Keep the last evaluated context per field and consumer. Weak consumer keys
 * bound retention to live widgets rather than their expression history.
 * @param {Object} record
 * @param {string} fieldName
 * @param {string} [rawContext]
 * @param {object} [cacheOwner]
 * @returns {Object}
 */
export function getFieldContext(
    record,
    fieldName,
    rawContext = record.activeFields[fieldName].context,
    cacheOwner = record,
) {
    const fresh = computeFieldContext(record, fieldName, rawContext);
    let contextsByField = CONTEXT_MEMO.get(record);
    if (!contextsByField) {
        contextsByField = new Map();
        CONTEXT_MEMO.set(record, contextsByField);
    }
    let contextsByOwner = contextsByField.get(fieldName);
    if (!contextsByOwner) {
        contextsByOwner = new WeakMap();
        contextsByField.set(fieldName, contextsByOwner);
    }
    const previous = contextsByOwner.get(cacheOwner);
    const equivalent = !!previous && shallowEqual(previous, fresh, deepEqual);
    log.logic("context lookup", () => ({
        fieldName,
        previous: !!previous,
        equivalent,
    }));
    if (equivalent) {
        return previous;
    }
    contextsByOwner.set(cacheOwner, fresh);
    return fresh;
}

/**
 * @param {Object} record
 * @param {string} fieldName
 * @param {*} domain
 * @returns {*}
 */
export function getFieldDomain(record, fieldName, domain) {
    if (typeof domain === "function") {
        domain = domain(record);
    }
    if (domain) {
        return domain;
    }
    domain = record.fields[fieldName].domain;
    return typeof domain === "string"
        ? new Domain(evaluateExpr(domain, record.evalContext)).toList()
        : domain || [];
}

/**
 * @param {{ context: Record<string, any> }} config
 * @returns {{ context: Object, uid: number, allowed_company_ids: number[], current_company_id: number | undefined }}
 */
export function getBasicEvalContext(config) {
    const { uid, allowed_company_ids } = config.context;
    return {
        context: config.context,
        uid,
        allowed_company_ids,
        current_company_id: allowed_company_ids?.[0],
    };
}

/**
 * @param {{ context: Record<string, any> }} config
 * @returns {Record<string, any>}
 */
export function getSpecEvalContext(config) {
    return { ...config.context, ...getBasicEvalContext(config) };
}

let nextId = 0;
/**
 * @param {string} [prefix]
 * @returns {string}
 */
export function getId(prefix = "") {
    return `${prefix}_${++nextId}`;
}

/**
 * @param {any} field
 * @returns {boolean}
 */
export function isRelational(field) {
    return field && ["one2many", "many2many", "many2one"].includes(field.type);
}
