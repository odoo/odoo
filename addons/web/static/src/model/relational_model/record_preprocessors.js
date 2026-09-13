// @ts-check
/** @odoo-module native */

import { markup } from "@odoo/owl";
import { isX2ManyType } from "@web/core/field_types";
import { x2ManyCommands } from "@web/core/network/commands";
import { _t } from "@web/core/translation";

import { getFieldContext, getSpecEvalContext } from "./field_context.js";
import { getFieldsSpec } from "./field_spec.js";

/** @import { RelationalRecord } from "@web/model/relational_model/record" */

/**
 * @param {RelationalRecord} record
 * @param {{ id?: number, display_name?: string }} value
 * @param {string} fieldName
 * @param {string} resModel
 * @returns {Promise<false | { id: number, display_name: string }>}
 */
export async function completeMany2OneValue(record, value, fieldName, resModel) {
    const resId = value.id;
    const displayName = value.display_name;
    if (!resId && !displayName) {
        return false;
    }
    const context = getFieldContext(record, fieldName);
    if (!resId && displayName !== undefined) {
        const pair = await record.model.orm.call(
            resModel,
            "name_create",
            [displayName],
            { context },
        );
        return pair && { id: pair[0], display_name: pair[1] };
    }
    if (resId && displayName === undefined) {
        const fieldSpec = { display_name: {} };
        if (record.activeFields[fieldName].related) {
            Object.assign(
                fieldSpec,
                getFieldsSpec(
                    record.activeFields[fieldName].related.activeFields,
                    record.activeFields[fieldName].related.fields,
                    getSpecEvalContext(record.config),
                ),
            );
        }
        const kwargs = { context, specification: fieldSpec };
        const records = await record.model.orm.webRead(resModel, [resId], kwargs);
        return records[0];
    }
    return /** @type {{ id: number, display_name: string }} */ (value);
}

/**
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 */
export async function preprocessMany2oneChanges(record, changes) {
    const proms = Object.entries(changes)
        .filter(([fieldName]) => record.fields[fieldName].type === "many2one")
        .map(async ([fieldName, value]) => {
            if (!value) {
                changes[fieldName] = false;
            } else if (record.activeFields[fieldName]) {
                const relation = /** @type {string} */ (
                    record.fields[fieldName].relation
                );
                return completeMany2OneValue(record, value, fieldName, relation).then(
                    (v) => {
                        changes[fieldName] = v;
                    },
                );
            }
        });
    return Promise.all(proms);
}

/**
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 */
export async function preprocessMany2OneReferenceChanges(record, changes) {
    const proms = Object.entries(changes)
        .filter(([fieldName]) => record.fields[fieldName].type === "many2one_reference")
        .map(async ([fieldName, value]) => {
            if (!value) {
                changes[fieldName] = false;
            } else if (typeof value === "number") {
                changes[fieldName] = { resId: value };
            } else {
                const relation = /** @type {Record<string, any>} */ (record.data)[
                    record.fields[fieldName].model_field
                ];
                return completeMany2OneValue(
                    record,
                    { id: value.resId, display_name: value.displayName },
                    fieldName,
                    relation,
                ).then((v) => {
                    if (!v) {
                        changes[fieldName] = false;
                        return;
                    }
                    const m2o = /** @type {{ id: number, display_name: string }} */ (v);
                    changes[fieldName] = {
                        resId: m2o.id,
                        displayName: m2o.display_name,
                    };
                });
            }
        });
    return Promise.all(proms);
}

/**
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 */
export async function preprocessReferenceChanges(record, changes) {
    const proms = Object.entries(changes)
        .filter(([fieldName]) => record.fields[fieldName].type === "reference")
        .map(async ([fieldName, value]) => {
            if (!value) {
                changes[fieldName] = false;
            } else {
                return completeMany2OneValue(
                    record,
                    { id: value.resId, display_name: value.displayName },
                    fieldName,
                    value.resModel,
                ).then((v) => {
                    if (!v) {
                        changes[fieldName] = false;
                        return;
                    }
                    const m2o = /** @type {{ id: number, display_name: string }} */ (v);
                    changes[fieldName] = {
                        resId: m2o.id,
                        resModel: value.resModel,
                        displayName: m2o.display_name,
                    };
                });
            }
        });
    return Promise.all(proms);
}

/**
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 */
export async function preprocessX2manyChanges(record, changes) {
    for (const [fieldName, value] of Object.entries(changes)) {
        if (!isX2ManyType(record.fields[fieldName].type)) {
            continue;
        }
        const list = /** @type {Record<string, any>} */ (record.data)[fieldName];
        let batch = [];
        for (const command of value) {
            if (command[0] === x2ManyCommands.SET) {
                if (batch.length) {
                    await list.applyCommandsLocked(batch);
                    batch = [];
                }
                await list.replaceWith(command[2]);
            } else {
                batch.push(command);
            }
        }
        if (batch.length) {
            await list.applyCommandsLocked(batch);
        }
        changes[fieldName] = list;
    }
}

/**
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 */
export function preprocessPropertiesChanges(record, changes) {
    const relatedChanges = Object.fromEntries(
        Object.entries(changes).filter(
            ([name]) => record.fields[name]?.relatedPropertyField,
        ),
    );
    for (const [fieldName, value] of Object.entries(changes)) {
        const field = record.fields[fieldName];
        if (field.type === "properties") {
            const definitionRecord = /** @type {string} */ (field.definition_record);
            const parent =
                changes[definitionRecord] ||
                /** @type {Record<string, any>} */ (record.data)[definitionRecord];
            Object.assign(
                changes,
                record.processProperties(value, fieldName, parent, record.data),
            );
        }
    }
    // Explicit dotted edits take precedence over the aggregate, regardless of
    // the insertion order of the keys in an update.
    Object.assign(changes, relatedChanges);
    preprocessRelatedPropertyChanges(record, changes, Object.keys(relatedChanges));
}

/**
 * Compose the aggregate from the current dotted values. This also runs after
 * asynchronous relation completion, which can replace those values.
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 * @param {string[]} fieldNames Explicit dotted edits, not fields derived from an aggregate.
 */
export function preprocessRelatedPropertyChanges(record, changes, fieldNames) {
    for (const fieldName of fieldNames) {
        if (!Object.hasOwn(changes, fieldName)) {
            continue;
        }
        const value = changes[fieldName];
        const field = record.fields[fieldName];
        if (field?.relatedPropertyField) {
            const [propertyFieldName, propertyName] = field.name.split(".");
            const propertiesData =
                changes[propertyFieldName] ||
                /** @type {Record<string, any>} */ (record.data)[propertyFieldName] ||
                [];
            if (
                !propertiesData.find(
                    (/** @type {any} */ property) => property.name === propertyName,
                )
            ) {
                record.model.uiHooks.onDisplayPropertyWarning(
                    _t(
                        "This record belongs to a different parent so you can not change this property.",
                    ),
                );
                delete changes[fieldName];
                continue;
            }
            changes[propertyFieldName] = propertiesData.map(
                (/** @type {any} */ property) =>
                    property.name === propertyName
                        ? {
                              ...property,
                              value:
                                  field.type === "many2many" && value?.records
                                      ? getPropertyListValue(
                                            value,
                                            record.data[propertyFieldName]?.find(
                                                (property) =>
                                                    property.name === propertyName,
                                            )?.value,
                                        )
                                      : value,
                          }
                        : property,
            );
        }
    }
}

/**
 * Properties serialize complete membership, not the visible page of a list.
 * @param {import("./static_list").StaticList} list
 * @param {[number, string][] | false | undefined} previousValue
 */
function getPropertyListValue(list, previousValue) {
    const previousNames = new Map(previousValue || []);
    return list.currentIds.map((id) => {
        const record = list.getCachedRecord(id);
        return [
            record?.resId || id,
            record?.data.display_name ?? previousNames.get(/** @type {number} */ (id)),
        ];
    });
}

/**
 * @param {RelationalRecord} record
 * @param {Record<string, any>} changes
 */
export function preprocessHtmlChanges(record, changes) {
    for (const [fieldName, value] of Object.entries(changes)) {
        if (record.fields[fieldName].type === "html") {
            changes[fieldName] = value === false ? false : markup(value);
        }
    }
}
