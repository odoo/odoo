// @ts-check

/** @module @web/model/relational_model/field_context - Context and domain resolution for relational fields */

import { makeContext } from "@web/core/context";
import { Domain } from "@web/core/domain";
import { evaluateExpr } from "@web/core/py_js/py";
import { user } from "@web/services/user";

/**
 * @param {Object} record
 * @param {string} fieldName
 * @param {string} [rawContext]
 * @returns {Object}
 */
export function getFieldContext(
    record,
    fieldName,
    rawContext = record.activeFields[fieldName].context,
) {
    const context = {};
    for (const key in record.context) {
        if (
            !key.startsWith("default_") &&
            !key.startsWith("search_default_") &&
            !key.endsWith("_view_ref")
        ) {
            context[key] = record.context[key];
        }
    }

    return {
        ...context,
        ...record.fields[fieldName].context,
        ...makeContext([rawContext], record.evalContext),
    };
}

/**
 * @param {Object} record
 * @param {string} fieldName
 * @param {*} domain
 * @returns {*}
 */
export function getFieldDomain(record, fieldName, domain) {
    if (typeof domain === "function") {
        domain = domain();
    }
    if (domain) {
        return domain;
    }
    // Fallback to the domain defined in the field definition in python
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
        current_company_id: user.activeCompany?.id,
    };
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
